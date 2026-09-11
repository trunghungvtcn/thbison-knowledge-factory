# VPS B — gate trước staging
Chưa có SSH hoặc audit VPS trong gói này. Không có lệnh tự ghi hạ tầng hiện tại.
1. Read-only inventory: OS/arch, RAM/disk, Docker/Compose versions, ports, services, reverse proxy, user deploy, backup location. Không in env/credential ra log.
2. Gate local: npm clean install/build/typecheck + core contracts + actual process E2E + persistence restart + auth/project isolation + no-public-effects. Báo đúng blockers.
3. Tạo /opt/thbison-content-os/releases/<release-id> hoặc path owner cấp, không ghi đè app đang chạy. Secrets file quyền 0600 ngoài source; DB/volume mới. Backup config và DB/volume liên quan trước migration; test restore trên volume riêng.
4. deploy/compose.mock.yml chỉ lab template, chưa được Docker validate ở reviewer. Codex phải build/kiểm tra config/health và chỉnh production server command trước staging. Không dùng vendor vite dev làm production server.
5. Up bằng project name riêng, host ports localhost; health + request auth + Planning→preview + restart→read + dry-run effect=0. Chỉ reverse proxy sau khi auth/session sẵn sàng và domain thật được cấp.
6. Rollback: giữ release trước và backup; stop project mới, khôi phục routing. Không compose down -v. Migration không tương thích cần restore DB riêng từ backup, không tự downgrade destructive.
7. Báo deploy status, actual bind/URL, image/source hashes, backup/restore results, remaining gates. Knowledge/CMS live OFF. Website VPS A không thuộc scope.
