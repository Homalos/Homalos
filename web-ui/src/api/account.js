import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * 获取最新的账户和持仓数据
 * @returns {Promise<Object>}
 */
export function getLatestAccountData() {
  return axios.get(`${API_BASE_URL}/api/account/latest`);
}

/**
 * 连接账户数据 WebSocket
 * @param {Function} onMessage - 消息回调函数
 * @param {Function} onError - 错误回调函数
 * @returns {WebSocket}
 */
export function connectAccountWebSocket(onMessage, onError) {
  const token = localStorage.getItem('token');
  const wsUrl = `${API_BASE_URL.replace(/^http/, 'ws')}/api/account/ws?token=${token}`;
  
  const ws = new WebSocket(wsUrl);
  
  ws.onopen = () => {
    console.log('[AccountWS] 连接已建立');
  };
  
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type !== 'ping') {
        onMessage(data);
      }
    } catch (error) {
      console.error('[AccountWS] 解析消息失败:', error);
      if (onError) {
        onError(error);
      }
    }
  };
  
  ws.onerror = (error) => {
    console.error('[AccountWS] 连接错误:', error);
    if (onError) {
      onError(error);
    }
  };
  
  ws.onclose = () => {
    console.log('[AccountWS] 连接已关闭');
  };
  
  return ws;
}

