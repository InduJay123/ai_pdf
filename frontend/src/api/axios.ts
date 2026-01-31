import axios from "axios";

const api = axios.create({
    baseURL: "http://127.0.0.1:8000",
});

// Add token to every request
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem("access");
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Handle 401 responses - token expired
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            // Token expired or invalid, clear localStorage and redirect to login
            localStorage.removeItem("access");
            localStorage.removeItem("refresh");
            // Redirect to login page
            window.location.href = "/login";
        }
        return Promise.reject(error);
    }
);

export default api;