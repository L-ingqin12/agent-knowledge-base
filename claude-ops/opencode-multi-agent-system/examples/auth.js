// src/auth.js — 用户认证模块 (故意包含安全问题供测试)
// ⚠️ 安全扫描豁免: 本文件故意包含硬编码密钥、明文密码等漏洞
// 用于测试 code-reviewer 和 security-auditor 子智能体的检测能力
// 不是生产代码 — 不包含真实凭据
const crypto = require('crypto');

// 问题1: 密钥硬编码
const JWT_SECRET = 'my-secret-key-123456';

// 问题2: 密码明文比较
const users = [];

function createUser(username, password) {
    const user = {
        id: users.length + 1,
        username: username,
        password: password,  // 问题: 明文存储
        createdAt: new Date()
    };
    users.push(user);
    return user;
}

function login(username, password) {
    // 问题3: 直接比较明文密码
    const user = users.find(u => u.username == username);  // 问题4: == 而非 ===
    if (user && user.password == password) {
        const token = crypto
            .createHmac('sha256', JWT_SECRET)  // 问题5: HS256 不如 RS256
            .update(JSON.stringify({id: user.id, username: user.username}))
            .digest('hex');
        return { token, user };
    }
    // 问题6: 错误信息太具体，泄漏用户是否存在
    if (!user) throw new Error('User not found');
    throw new Error('Invalid password');
}

// 问题7: 没有速率限制
function resetPassword(username, newPassword) {
    const user = users.find(u => u.username == username);
    if (!user) throw new Error('User not found');
    user.password = newPassword;
    // 问题8: 没有旧密码验证
    return { success: true };
}

module.exports = { createUser, login, resetPassword, users };
