# IOL Calculator API

这是一个基于Cloudflare Python Workers的IOL（人工晶体）度数计算API服务，支持AI图片识别功能。

## 功能特性

- 提供Barrett Universal II公式计算IOL度数
- 支持单眼或双眼计算
- **AI图片识别**：从IOL master晶体单图片中自动提取数据
- RESTful API接口
- 完整的错误处理和参数验证
- JSON格式的响应数据
- Web UI界面，支持可视化操作

## API 端点

### 1. 问候接口

**GET** `/hello` 或 `/`

返回服务基本信息和问候消息。

**响应示例：**
```json
{
  "message": "Hello World!",
  "service": "IOL Calculator API",
  "version": "1.0.0"
}
```

### 2. IOL计算接口

**POST** `/calculate`

计算IOL度数的主要接口。

**请求体格式：**
```json
{
  "right_eye": {
    "AL": 24.0,
    "K1": 42.0,
    "K2": 42.0,
    "ACD": 3.0,
    "Refraction": 0,
    "LenThickness": "",
    "WTW": ""
  },
  "left_eye": {
    "AL": 23.5,
    "K1": 43.0,
    "K2": 43.5,
    "ACD": 3.2,
    "Refraction": -0.5,
    "LenThickness": "",
    "WTW": ""
  },
  "a_constant": 119
}
```

**参数说明：**

#### 眼部参数（right_eye / left_eye）
- `AL`: 轴长（必需）
- `K1`: 角膜曲率1（必需）
- `K2`: 角膜曲率2（必需）
- `ACD`: 前房深度（可选，默认3.0）
- `Refraction`: 屈光度（可选，默认0）
- `LenThickness`: 晶状体厚度（可选）
- `WTW`: 白到白距离（可选）

#### 其他参数
- `a_constant`: A常数（可选，默认119）

**注意：** 至少需要提供右眼或左眼的参数。

**响应示例：**
```json
{
  "success": true,
  "data": {
    "surgeon_info": "1",
    "patient_info": "1",
    "right_eye": {
      "biometry": "...",
      "prediction": "...",
      "constants": "...",
      "iol_options": [
        {
          "iol_power": "20.0",
          "optic": "SA60AT",
          "refraction": "0.00",
          "recommended": true
        }
      ]
    },
    "left_eye": {
      "biometry": "...",
      "prediction": "...",
      "constants": "...",
      "iol_options": [
        {
          "iol_power": "21.5",
          "optic": "SA60AT",
          "refraction": "-0.50",
          "recommended": true
        }
      ]
    }
  },
  "message": "IOL计算完成"
}
```

## 错误响应

API会返回适当的HTTP状态码和错误信息：

- `400 Bad Request`: 参数验证失败
- `404 Not Found`: 路径不存在
- `405 Method Not Allowed`: HTTP方法不支持
- `415 Unsupported Media Type`: 请求体格式错误
- `500 Internal Server Error`: 服务器内部错误

**错误响应格式：**
```json
{
  "error": "Bad Request",
  "message": "右眼缺少必需参数: AL, K1, K2"
}
```

## 使用示例

### 1. 只计算右眼

```bash
curl -X POST https://barretcalcata.killgfat.com/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "right_eye": {
      "AL": 24.0,
      "K1": 42.0,
      "K2": 42.0
    }
  }'
```

### 2. 双眼计算

```bash
curl -X POST https://barretcalcata.killgfat.com/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "right_eye": {
      "AL": 24.0,
      "K1": 42.0,
      "K2": 42.0
    },
    "left_eye": {
      "AL": 23.5,
      "K1": 43.0,
      "K2": 43.5
    }
  }'
```

### 3. 自定义A常数

```bash
curl -X POST https://barretcalcata.killgfat.com/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "right_eye": {
      "AL": 24.0,
      "K1": 42.0,
      "K2": 42.0
    },
    "a_constant": 118.5
  }'
```

### 4. AI图片识别提取数据

**POST** `/extract-from-image`

使用AI从IOL master晶体单图片中自动提取测量数据。

**请求体格式：**
```json
{
  "image": "base64编码的图片数据"
}
```

**响应示例：**
```json
{
  "success": true,
  "data": {
    "patient_name": "张三",
    "a_constant": 119.3,
    "right_eye": {
      "AL": 24.0,
      "K1": 42.0,
      "K2": 42.0,
      "ACD": 3.0
    },
    "left_eye": {
      "AL": 23.5,
      "K1": 43.0,
      "K2": 43.5,
      "ACD": 3.2
    }
  },
  "message": "图片数据提取成功"
}
```

**使用示例：**
```bash
# 首先将图片转换为base64
IMAGE_BASE64=$(base64 -w 0 iol_master_report.jpg)

# 然后发送请求
curl -X POST https://barretcalcata.killgfat.com/extract-from-image \
  -H "Content-Type: application/json" \
  -d "{\"image\": \"$IMAGE_BASE64\"}"
```

### 5. Web UI界面

**GET** `/`

访问Web UI界面，提供可视化的操作界面，支持：
- 手动输入参数计算
- 上传图片自动识别数据
- 实时计算结果展示

直接在浏览器中访问：`https://barretcalcata.killgfat.com`

## 配置

### OpenAI API配置

在使用AI图片识别功能之前，需要配置OpenAI API：

1. **设置API密钥**（必需）：
   ```bash
   wrangler secret put OPENAI_API_KEY
   ```
   然后输入你的OpenAI API密钥。

2. **配置API URL**（可选）：
   默认使用 `https://api.openai.com/v1/chat/completions`，如需使用其他兼容API，可在 `wrangler.jsonc` 中配置：
   ```json
   "vars": { 
     "OPENAI_API_URL": "https://your-api-endpoint.com/v1/chat/completions",
     "OPENAI_MODEL": "gpt-4-vision-preview"
   }
   ```

3. **配置模型**（可选）：
   默认使用 `gpt-4-vision-preview`，可在环境变量中修改为其他支持图片的模型。

## 部署

1. 确保已安装Cloudflare Workers CLI (`wrangler`)
2. 配置OpenAI API密钥（见上）
3. 在项目目录中运行：
   ```bash
   wrangler deploy
   ```

## 技术栈

- **Cloudflare Workers**: 无服务器计算平台
- **Python**: 编程语言
- **BeautifulSoup4**: HTML解析
- **Requests**: HTTP客户端
- **workers-py**: Cloudflare Workers Python SDK

## 注意事项

- 该API依赖于外部计算服务，响应时间可能受网络影响
- 请确保提供准确的测量参数以获得可靠的计算结果
- 计算结果仅供参考，实际临床应用请咨询专业眼科医生
