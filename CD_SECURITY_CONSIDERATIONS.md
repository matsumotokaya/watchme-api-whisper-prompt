# CD（継続的デプロイ）セキュリティ考慮事項

## 🔒 概要

EC2への自動デプロイ（CD）を実装する際の重要なセキュリティ考慮事項をまとめています。

## ⚠️ リスクと対策

### 1. SSH秘密鍵の管理

#### リスク
- 秘密鍵が漏洩すると、EC2サーバーへの不正アクセスが可能になる
- GitHub Secretsが侵害されると、本番環境が危険にさらされる

#### 対策
```yaml
# ✅ 推奨: 専用のデプロイキーを作成
EC2_SSH_PRIVATE_KEY: deploy-only-key.pem

# ❌ 避ける: 管理者用キーの使用
EC2_SSH_PRIVATE_KEY: admin-key.pem
```

**実装方法:**
```bash
# EC2で専用デプロイユーザーを作成
sudo adduser deploy-user
sudo mkdir /home/deploy-user/.ssh
sudo cp ~/.ssh/authorized_keys /home/deploy-user/.ssh/
sudo chown -R deploy-user:deploy-user /home/deploy-user/.ssh

# sudoersに必要最小限の権限を付与
echo "deploy-user ALL=(ALL) NOPASSWD: /usr/bin/docker, /usr/bin/docker-compose" | sudo tee /etc/sudoers.d/deploy-user
```

### 2. ネットワークアクセス制限

#### 現在の設定（改善の余地あり）
```yaml
# 現在: StrictHostKeyCheckingを無効化
ssh -o StrictHostKeyChecking=no
```

#### 推奨設定
```yaml
# Known Hostsを事前登録（実装済み）
ssh-keyscan -H ${{ secrets.EC2_HOST }} >> ~/.ssh/known_hosts
```

### 3. 実行権限の最小化

#### 原則
- デプロイに必要な最小限の権限のみ付与
- rootアクセスは避ける
- 特定のディレクトリのみアクセス可能に

#### 実装例
```bash
# /home/ubuntu/watchme-api-vibe-aggregator のみアクセス可能
# run-prod.sh のみ実行可能
```

## 🛡️ 多層防御アプローチ

### レイヤー1: GitHub Actions
```yaml
# ブランチ保護
on:
  push:
    branches: [ "main" ]  # mainブランチのみ

# 環境変数による制御
if: github.ref == 'refs/heads/main'
```

### レイヤー2: AWS IAM
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "ecr:GetAuthorizationToken",
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer"
    ],
    "Resource": "arn:aws:ecr:*:*:repository/watchme-api-vibe-aggregator"
  }]
}
```

### レイヤー3: EC2セキュリティグループ
```bash
# SSH接続元を制限（GitHub ActionsのIPレンジのみ許可）
# ポート22: GitHub Actions CIDR blocks only
```

### レイヤー4: コンテナレベル
```yaml
# Docker実行時の制限
docker run --read-only --security-opt=no-new-privileges
```

## 📊 監査とモニタリング

### GitHub Actions監査
```bash
# 実行履歴の確認
https://github.com/[org]/[repo]/actions

# 監視すべき項目:
- 予期しない時間のデプロイ
- 失敗の繰り返し
- 不明なアクターによる実行
```

### EC2サーバー監査
```bash
# SSH接続ログ
sudo tail -f /var/log/auth.log | grep sshd

# Dockerイベント
docker events --filter event=start

# デプロイログ
tail -f /var/log/deploy.log
```

## 🔄 定期的なセキュリティレビュー

### 月次チェックリスト
- [ ] GitHub Secretsのアクセス履歴確認
- [ ] 不要なシークレットの削除
- [ ] SSH鍵のローテーション検討
- [ ] EC2のセキュリティパッチ適用
- [ ] Dockerイメージの脆弱性スキャン

### 四半期チェックリスト
- [ ] SSH鍵の更新
- [ ] IAMポリシーの見直し
- [ ] セキュリティグループルールの確認
- [ ] 監査ログの分析

## 🚨 インシデント対応

### 漏洩が疑われる場合

1. **即座に無効化**
   ```bash
   # GitHub Secretsを削除
   Settings → Secrets → Delete
   
   # EC2のauthorized_keysから削除
   ssh ubuntu@3.24.16.82
   nano ~/.ssh/authorized_keys  # 該当キーを削除
   ```

2. **新しいキーペアを生成**
   ```bash
   ssh-keygen -t rsa -b 4096 -f new-deploy-key
   ```

3. **影響調査**
   - デプロイ履歴の確認
   - 不正なコンテナの確認
   - ログの詳細分析

## 💡 ベストプラクティス

### DO ✅
- 専用のデプロイキーを使用
- 最小権限の原則を適用
- すべてのデプロイをログに記録
- 定期的なキーローテーション
- 環境ごとに異なるキーを使用

### DON'T ❌
- 管理者キーをCDに使用
- StrictHostKeyCheckingを恒久的に無効化
- root権限でデプロイ実行
- 秘密鍵をコードにハードコード
- 監査ログを無視

## 🔮 将来的な改善案

### 短期（1-3ヶ月）
- [ ] Slack通知の実装
- [ ] デプロイ承認フローの追加
- [ ] 専用デプロイユーザーの作成

### 中期（3-6ヶ月）
- [ ] AWS Systems Managerへの移行（SSHレス）
- [ ] HashiCorp Vaultによるシークレット管理
- [ ] 自動ロールバック機能

### 長期（6ヶ月以上）
- [ ] Blue/Greenデプロイメント
- [ ] カナリアリリース
- [ ] 完全なゼロトラストアーキテクチャ

## 📚 参考資料

- [GitHub Actions Security Best Practices](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
- [AWS Security Best Practices](https://aws.amazon.com/security/best-practices/)
- [Docker Security](https://docs.docker.com/engine/security/)
- [SSH Security Guidelines](https://www.ssh.com/academy/ssh/security)