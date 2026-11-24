import axios from "axios";

const LOGIN_REQUIRED_EVENT = "shengyu:login-required";

/**
 * 学生端功能接口共用工厂：游客触发写接口时后端返回
 * 403 + detail.code=login_required，这里统一派发事件，由全局弹窗引导登录。
 */
export function createApi(baseURL) {
  const instance = axios.create({ baseURL, withCredentials: true });
  instance.interceptors.response.use(
    (response) => response,
    (error) => {
      const status = error?.response?.status;
      const detail = error?.response?.data?.detail;
      if (status === 403 && detail && typeof detail === "object" && detail.code === "login_required") {
        window.dispatchEvent(new CustomEvent(LOGIN_REQUIRED_EVENT));
      }
      return Promise.reject(error);
    }
  );
  return instance;
}

export { LOGIN_REQUIRED_EVENT };
