/**
 * API 请求封装
 * =============
 * 基于 wx.request 的 Promise 封装，统一处理错误。
 */

const config = require('./config');

/**
 * 通用请求
 * @param {string} path - API 路径 (如 '/api/predict/basic')
 * @param {object} data - 请求体
 * @returns {Promise<object>} 解析后的 data 对象
 */
function request(path, data) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: config.API_BASE_URL + path,
      method: 'POST',
      header: {
        'Content-Type': 'application/json',
        'ngrok-skip-browser-warning': '1',  // 绕过 ngrok 免费版警告页
      },
      data: data,
      timeout: 30000,
      success(res) {
        if (res.statusCode === 200) {
          const body = res.data;
          // ngrok 警告页返回 HTML 而非 JSON
          if (typeof body !== 'object' || body === null) {
            reject(new Error('响应格式异常，请检查 API 地址是否正确'));
            return;
          }
          if (body.code === 0) {
            resolve(body.data);
          } else {
            reject(new Error(body.message || '请求失败'));
          }
        } else {
          reject(new Error(`服务器错误 (HTTP ${res.statusCode})`));
        }
      },
      fail(err) {
        console.error('wx.request 失败:', err);
        reject(new Error('网络请求失败，请检查：\n1. Flask 后端是否已启动\n2. API 地址是否正确\n3. 微信开发者工具是否勾选"不校验合法域名"'));
      },
    });
  });
}

/**
 * 基础筛查 (6 项)
 */
function predictBasic(data) {
  return request('/api/predict/basic', data);
}

/**
 * 深度筛查 (16 项)
 */
function predictAdvanced(data) {
  return request('/api/predict/advanced', data);
}

module.exports = {
  predictBasic,
  predictAdvanced,
};
