import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
    plugins: [react()],
    server: {
        host: "127.0.0.1",
        port: 5173,
        proxy: {
            "/canary-admin": {
                target: "http://127.0.0.1:6000",
                changeOrigin: true,
                rewrite: function (path) { return path.replace(/^\/canary-admin/, ""); },
            },
            "/canary-gateway": {
                target: "http://127.0.0.1:6001",
                changeOrigin: true,
                rewrite: function (path) { return path.replace(/^\/canary-gateway/, ""); },
            },
        },
    },
});
