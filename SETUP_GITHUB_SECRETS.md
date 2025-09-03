# GitHub Actions シークレット設定手順

このドキュメントでは、GitHub ActionsでECRへの自動デプロイを有効にするための設定手順を説明します。

## 📝 必要な準備

以下の情報を準備してください：
- **AWS Access Key ID**: AWS IAMユーザーのアクセスキーID
- **AWS Secret Access Key**: AWS IAMユーザーのシークレットアクセスキー

## 🔐 GitHub シークレットの設定手順

### ステップ 1: GitHubリポジトリを開く

1. ブラウザで以下のリポジトリを開きます：
   ```
   https://github.com/[your-username]/api_gen-prompt_mood-chart_v1
   ```

### ステップ 2: Settings（設定）にアクセス

1. リポジトリの上部メニューから **「Settings」** をクリック
   ![Settings location](設定タブは右端にあります)

### ステップ 3: Secrets and variables を開く

1. 左サイドバーの **「Security」** セクションを見つける
2. **「Secrets and variables」** をクリック
3. サブメニューから **「Actions」** をクリック

### ステップ 4: シークレットを追加

#### AWS_ACCESS_KEY_ID の追加

1. **「New repository secret」** ボタンをクリック
2. 以下を入力：
   - **Name**: `AWS_ACCESS_KEY_ID`
   - **Secret**: あなたのAWS Access Key ID（例: `AKIAIOSFODNN7EXAMPLE`）
3. **「Add secret」** ボタンをクリック

#### AWS_SECRET_ACCESS_KEY の追加

1. 再度 **「New repository secret」** ボタンをクリック
2. 以下を入力：
   - **Name**: `AWS_SECRET_ACCESS_KEY`
   - **Secret**: あなたのAWS Secret Access Key
3. **「Add secret」** ボタンをクリック

## ✅ 設定完了の確認

設定が完了すると、以下のように2つのシークレットが表示されます：

```
Repository secrets (2)
• AWS_ACCESS_KEY_ID - Updated now
• AWS_SECRET_ACCESS_KEY - Updated now
```

## 🚀 自動デプロイのテスト

### 方法1: 手動実行でテスト

1. リポジトリの **「Actions」** タブをクリック
2. 左サイドバーから **「Deploy to Amazon ECR」** をクリック
3. 右側の **「Run workflow」** ボタンをクリック
4. **「Run workflow」** を再度クリックして実行

### 方法2: コードをpushしてテスト

```bash
# テスト用の小さな変更を加える
echo "# CI/CD Test" >> README.md

# コミット＆プッシュ
git add README.md
git commit -m "test: CI/CD pipeline"
git push origin main
```

## 📊 実行状況の確認

1. **「Actions」** タブで実行状況を確認
2. ワークフロー名をクリックして詳細を表示
3. 各ステップの✅または❌を確認

### 成功時の表示例

```
✅ Checkout code
✅ Configure AWS credentials
✅ Login to Amazon ECR
✅ Build, tag, and push image to Amazon ECR
✅ Deploy Success Notification
```

## 🔧 トラブルシューティング

### エラー: Invalid AWS credentials

- **原因**: AWS認証情報が正しくない
- **解決策**: シークレットの値を再確認し、正しいキーを設定

### エラー: ECR repository not found

- **原因**: ECRリポジトリが存在しない
- **解決策**: AWSコンソールでECRリポジトリが作成されているか確認

### エラー: Permission denied

- **原因**: IAMユーザーに必要な権限がない
- **解決策**: IAMユーザーに以下の権限があるか確認：
  - `ecr:GetAuthorizationToken`
  - `ecr:BatchCheckLayerAvailability`
  - `ecr:PutImage`
  - `ecr:InitiateLayerUpload`
  - `ecr:UploadLayerPart`
  - `ecr:CompleteLayerUpload`

## 📚 参考リンク

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Configuring AWS Credentials for GitHub Actions](https://github.com/aws-actions/configure-aws-credentials)
- [Amazon ECR Login Action](https://github.com/aws-actions/amazon-ecr-login)