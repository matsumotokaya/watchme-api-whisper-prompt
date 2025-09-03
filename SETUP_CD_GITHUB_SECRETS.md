# CD（継続的デプロイ）用 GitHub Secrets 設定手順

このドキュメントでは、EC2への自動デプロイを有効にするために必要な追加のGitHub Secretsの設定手順を説明します。

## ⚠️ 重要なセキュリティ注意事項

**SSH秘密鍵は極めて重要な認証情報です。以下の点に十分注意してください：**
- 絶対に他人と共有しない
- コードやコメントに直接記載しない
- 定期的にキーをローテーションする
- 不要になったら速やかに削除する

## 📝 必要な追加シークレット

CI（ECRプッシュ）用のシークレットに加えて、以下が必要です：

| シークレット名 | 説明 | 値の例 |
|--------------|------|--------|
| `EC2_SSH_PRIVATE_KEY` | EC2接続用SSH秘密鍵 | watchme-key.pemの内容 |
| `EC2_HOST` | EC2サーバーのIPアドレス | `3.24.16.82` |
| `EC2_USER` | EC2のユーザー名 | `ubuntu` |

## 🔐 設定手順

### ステップ 1: SSH秘密鍵を準備

1. **watchme-key.pem ファイルを開く**
   ```bash
   # ターミナルで内容を表示
   cat ~/watchme-key.pem
   ```

2. **内容を全てコピー**
   - `-----BEGIN RSA PRIVATE KEY-----` から
   - `-----END RSA PRIVATE KEY-----` まで
   - **全ての行を含めてコピー**

### ステップ 2: GitHub でシークレットを設定

#### 2-1: EC2_SSH_PRIVATE_KEY の追加

1. GitHubリポジトリを開く
2. **Settings** → **Secrets and variables** → **Actions**
3. **New repository secret** をクリック
4. 以下を入力：
   - **Name**: `EC2_SSH_PRIVATE_KEY`
   - **Secret**: コピーしたSSH秘密鍵の内容を貼り付け
5. **Add secret** をクリック

**注意点:**
- 改行も含めて正確にコピー＆ペースト
- 余分な空白や改行を追加しない
- ペースト後、先頭と末尾に余分な空白がないか確認

#### 2-2: EC2_HOST の追加

1. **New repository secret** をクリック
2. 以下を入力：
   - **Name**: `EC2_HOST`
   - **Secret**: `3.24.16.82`
3. **Add secret** をクリック

#### 2-3: EC2_USER の追加

1. **New repository secret** をクリック
2. 以下を入力：
   - **Name**: `EC2_USER`
   - **Secret**: `ubuntu`
3. **Add secret** をクリック

## ✅ 設定完了の確認

設定が完了すると、以下の5つのシークレットが表示されるはずです：

```
Repository secrets (5)
• AWS_ACCESS_KEY_ID - Updated X minutes ago
• AWS_SECRET_ACCESS_KEY - Updated X minutes ago
• EC2_SSH_PRIVATE_KEY - Updated now
• EC2_HOST - Updated now
• EC2_USER - Updated now
```

## 🧪 CDのテスト方法

### 方法1: テストブランチで確認（推奨）

```bash
# テストブランチを作成
git checkout -b test-cd

# 小さな変更を加える
echo "# CD Test $(date)" >> README.md

# コミット＆プッシュ
git add README.md
git commit -m "test: CD pipeline"
git push origin test-cd

# mainブランチにマージ
git checkout main
git merge test-cd
git push origin main
```

### 方法2: GitHub Actions UIから手動実行

1. リポジトリの **Actions** タブを開く
2. 左サイドバーから **Deploy to Amazon ECR and EC2** をクリック
3. **Run workflow** → **Run workflow** をクリック

## 📊 実行結果の確認

### 成功時の表示

Actions タブで以下のような流れが表示されます：

```
Deploy to Amazon ECR and EC2
├─ Deploy Image ✅
│  ├─ Checkout code ✅
│  ├─ Configure AWS credentials ✅
│  ├─ Login to Amazon ECR ✅
│  └─ Build, tag, and push image ✅
│
└─ Deploy to EC2 ✅
   ├─ Setup SSH Agent ✅
   ├─ Add EC2 to known hosts ✅
   ├─ Deploy to EC2 instance ✅
   └─ Deployment Success Notification ✅
```

### EC2サーバーでの確認

```bash
# SSH接続
ssh -i ~/watchme-key.pem ubuntu@3.24.16.82

# コンテナの状態確認
docker ps | grep api_gen_prompt_mood_chart

# ログ確認
docker logs api_gen_prompt_mood_chart --tail 20

# 外部からヘルスチェック
curl https://api.hey-watch.me/vibe-aggregator/health
```

## 🔧 トラブルシューティング

### エラー: Permission denied (publickey)

**原因**: SSH秘密鍵が正しく設定されていない

**解決方法**:
1. `EC2_SSH_PRIVATE_KEY` の内容を再確認
2. 改行コードが正しいか確認（LFである必要がある）
3. ローカルで同じキーを使ってSSH接続できるか確認
   ```bash
   ssh -i ~/watchme-key.pem ubuntu@3.24.16.82
   ```

### エラー: Host key verification failed

**原因**: Known hostsにEC2が登録されていない

**解決方法**:
- ワークフローの `ssh-keyscan` ステップが正常に動作しているか確認
- `EC2_HOST` シークレットが正しいIPアドレスか確認

### エラー: ./run-prod.sh: Permission denied

**原因**: 実行権限がない

**解決方法**:
```bash
# EC2サーバーで実行権限を付与
ssh -i ~/watchme-key.pem ubuntu@3.24.16.82
chmod +x /home/ubuntu/watchme-api-vibe-aggregator/run-prod.sh
```

### エラー: docker-compose: command not found

**原因**: EC2にDocker Composeがインストールされていない

**解決方法**:
```bash
# EC2サーバーでインストール
ssh -i ~/watchme-key.pem ubuntu@3.24.16.82
sudo apt-get update
sudo apt-get install docker-compose -y
```

## 🔒 セキュリティのベストプラクティス

1. **最小権限の原則**
   - デプロイ専用のSSHキーを作成することを検討
   - 必要最小限のディレクトリのみアクセス可能に

2. **キーのローテーション**
   - 定期的（3-6ヶ月ごと）にSSHキーを更新
   - 古いキーは速やかに削除

3. **監査ログ**
   - GitHub Actionsの実行履歴を定期的に確認
   - 不審なデプロイがないかチェック

4. **環境の分離**
   - 本番用と開発用でSSHキーを分ける
   - 本番環境へのアクセスは制限する

5. **通知の設定**
   - デプロイ実行時にSlack等へ通知
   - 失敗時はアラートを送信

## 📚 参考リンク

- [GitHub Encrypted Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [SSH Agent Action](https://github.com/webfactory/ssh-agent)
- [GitHub Actions Security Best Practices](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)