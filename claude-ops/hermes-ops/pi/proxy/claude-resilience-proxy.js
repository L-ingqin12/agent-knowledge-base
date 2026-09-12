#!/usr/bin/env node
const http = require("http");
const https = require("https");
const { URL } = require("url");

const PORT = parseInt(process.env.PROXY_PORT || "8787");
const TARGET = process.env.PROXY_TARGET || "https://ark.cn-beijing.volces.com/api/coding";
const TARGET_URL = new URL(TARGET);
const RETRIES = 3;
const BACKOFF = [1000, 3000, 8000];

const isHttps = TARGET_URL.protocol === "https:";
const transport = isHttps ? https : http;
const defaultPort = isHttps ? 443 : 80;

function doRequest(opts, body, retries) {
  return new Promise((resolve, reject) => {
    const req = transport.request({
      hostname: TARGET_URL.hostname,
      port: TARGET_URL.port || defaultPort,
      path: TARGET_URL.pathname + opts.path,
      method: opts.method,
      headers: { ...opts.headers, host: TARGET_URL.hostname },
      timeout: 180000,
    }, (res) => {
      let data = [];
      res.on("data", c => data.push(c));
      res.on("end", () => resolve({
        status: res.statusCode,
        headers: res.headers,
        body: Buffer.concat(data),
      }));
      res.on("error", reject);
    });

    req.on("error", (err) => {
      const msg = err.message.toLowerCase();
      const retryable = ["socket", "econnreset", "etimedout", "closed",
                          "eof", "broken pipe", "read econnreset"].some(k => msg.includes(k));
      if (retryable && retries > 0) {
        const delay = BACKOFF[BACKOFF.length - retries] || 8000;
        console.error("[proxy] Retry in " + delay + "ms (" + retries + " left): " + err.message);
        setTimeout(() => doRequest(opts, body, retries - 1).then(resolve).catch(reject), delay);
      } else {
        reject(err);
      }
    });

    req.on("timeout", () => {
      req.destroy();
      if (retries > 0) {
        const delay = BACKOFF[BACKOFF.length - retries] || 8000;
        console.error("[proxy] Timeout, retry in " + delay + "ms (" + retries + " left)");
        setTimeout(() => doRequest(opts, body, retries - 1).then(resolve).catch(reject), delay);
      } else {
        reject(new Error("upstream timeout"));
      }
    });

    if (body) req.write(body);
    req.end();
  });
}

const server = http.createServer((clientReq, clientRes) => {
  const start = Date.now();
  let bodyChunks = [];
  clientReq.on("data", c => bodyChunks.push(c));
  clientReq.on("end", async () => {
    const body = Buffer.concat(bodyChunks);
    const fwdHeaders = {};
    for (const [k, v] of Object.entries(clientReq.headers)) {
      if (!["host","connection","keep-alive","transfer-encoding"].includes(k.toLowerCase())) {
        fwdHeaders[k] = v;
      }
    }
    try {
      const result = await doRequest({
        path: clientReq.url,
        method: clientReq.method,
        headers: fwdHeaders,
      }, body.length > 0 ? body : null, RETRIES);
      clientRes.writeHead(result.status, result.headers);
      clientRes.end(result.body);
      console.error("[proxy] " + clientReq.method + " " + clientReq.url + " -> " + result.status + " (" + (Date.now() - start) + "ms)");
    } catch (err) {
      clientRes.writeHead(502, { "Content-Type": "application/json" });
      clientRes.end(JSON.stringify({ error: { type: "proxy_error", message: err.message } }));
    }
  });
});

server.listen(PORT, "127.0.0.1", () => {
  console.error("[proxy] Listening 127.0.0.1:" + PORT + " -> " + TARGET);
  console.error("[proxy] Retries: " + RETRIES + ", backoff: " + BACKOFF.map(b => (b/1000)+"s").join("/"));
});
