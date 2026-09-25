# JobTrack Frontend

React、TypeScript 和 Vite 构建的 JobTrack Web 客户端。

## Requirements

- Node.js 24
- npm 11+
- Python/uv environment for the FastAPI project

## Commands

```bash
npm install
npm run generate:api
npm run dev
```

开发服务器固定运行在 `http://localhost:3000`，并将 API、认证和健康检查路径代理到 `http://127.0.0.1:8000`。

质量检查：

```bash
npm run lint
npm run typecheck
npm run test:e2e
npm run test:run
npm run build
```

`src/api/schema.d.ts` 由 `openapi.json` 生成，禁止手工修改。后端接口改变后应重新运行 `npm run generate:api` 并提交两个文件的更新。

## E2E

Playwright 测试连接真实 FastAPI 和 PostgreSQL。先启动测试 API，再安装 Chromium 并运行：

```bash
npm run test:e2e:install
npm run test:e2e
```

`VITE_API_PROXY_TARGET` 可覆盖 E2E 使用的 API 地址；CI 会保留失败截图、视频、trace 和 HTML 报告。

## Production container

从仓库根目录启动完整栈：

```bash
python scripts/dev.py stack-up
```

浏览器访问 `http://127.0.0.1:3000`。前端镜像由 Node 24 多阶段构建，运行时使用非 root Nginx，不包含 Node.js；Nginx 提供 SPA 回退、同源 API 代理、静态资源缓存和安全响应头。
