"""
Web UI模块 - 处理IOL计算器的Web界面
"""

INDEX_PAGE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IOL晶体计算器 - Barrett Universal II公式</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px; }
        .container { max-width: 1000px; margin: 0 auto; background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { background: #007bff; color: white; padding: 20px; border-radius: 10px 10px 0 0; display: flex; justify-content: space-between; align-items: center; position: relative; }
        .header-title { text-align: center; flex: 1; }
        .header-title h1 { margin: 0; font-size: 1.8em; }
        .header-title p { margin: 5px 0 0; opacity: 0.9; }
        .github-link { display: flex; align-items: center; justify-content: center; width: 40px; height: 40px; color: white; text-decoration: none; border-radius: 6px; transition: background 0.2s; }
        .github-link:hover { background: rgba(255,255,255,0.15); }
        .github-icon { width: 28px; height: 28px; fill: white; }
        .main-content { padding: 30px; }
        .form-section { margin-bottom: 30px; padding: 20px; border: 1px solid #ddd; border-radius: 8px; }
        .section-title { font-size: 1.5em; margin-bottom: 15px; color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: bold; color: #555; }
        .form-group input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; font-size: 16px; }
        .form-group input:focus { outline: none; border-color: #007bff; box-shadow: 0 0 5px rgba(0,123,255,0.3); }
        .eye-section { margin: 15px 0; padding: 20px; border: 1px solid #ccc; border-radius: 8px; transition: border-color 0.3s; }
        .eye-section.active { border-color: #007bff; background: #f8f9ff; }
        .eye-header { margin-bottom: 15px; }
        .eye-header input[type="checkbox"] { margin-right: 10px; transform: scale(1.2); }
        .eye-params { display: none; }
        .eye-params.show { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
        .btn { background: #007bff; color: white; padding: 15px 30px; border: none; border-radius: 5px; font-size: 16px; font-weight: bold; cursor: pointer; transition: background 0.3s; }
        .btn:hover { background: #0056b3; }
        .btn:disabled { background: #ccc; cursor: not-allowed; }
        .btn-container { text-align: center; margin-top: 20px; }
        .results-section { margin-top: 30px; display: none; }
        .results-section.show { display: block; }
        .result-card { margin-bottom: 20px; padding: 20px; border: 1px solid #ddd; border-radius: 8px; background: #fafafa; }
        .result-card h4 { color: #333; margin-bottom: 15px; font-size: 1.2em; }
        .result-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        .result-table th, .result-table td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        .result-table th { background: #f8f9fa; font-weight: bold; color: #555; }
        .result-table tr:hover { background: #f8f9fa; }
        .recommended { background: #d4edda !important; font-weight: bold; color: #155724; }
        .error-message { background: #f8d7da; color: #721c24; padding: 15px; border-radius: 5px; margin: 20px 0; border: 1px solid #f5c6cb; display: none; }
        .error-message.show { display: block; }
        .loading { text-align: center; padding: 20px; display: none; }
        .loading.show { display: block; }
        .spinner { border: 4px solid #f3f3f3; border-top: 4px solid #007bff; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto 10px; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .param-hint { font-size: 0.9em; color: #666; margin-top: 5px; }
        .suggestion-box {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 5px;
            padding: 10px;
            font-size: 0.85em;
            color: #856404;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            max-width: 100%;
            line-height: 1.4;
            word-wrap: break-word;
        }
        .suggestion-box .suggestion-title {
            font-weight: bold;
            color: #d63031;
            margin-bottom: 5px;
        }
        .suggestion-box .suggestion-content {
            font-size: 0.9em;
        }
        .form-group { position: relative; }
        @media (max-width: 768px) {
            .container { margin: 10px; }
            .main-content { padding: 20px; }
            .eye-params.show { grid-template-columns: 1fr; }
            .form-group input { width: 100%; max-width: 100%; }
            .suggestion-box { font-size: 0.8em; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-title">
                <h1>IOL晶体计算器</h1>
                <p>基于Barrett Universal II公式的人工晶体度数计算</p>
            </div>
            <a href="https://github.com/killgfat/barrettcalcata" target="_blank" class="github-link" title="查看源码">
                <svg class="github-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
                </svg>
            </a>
        </div>
        
        <div class="main-content">
            <form id="iolForm">
                <div class="form-section">
                    <h2 class="section-title">患者信息</h2>
                    <div class="form-group">
                        <label for="patientName">患者姓名（可选）</label>
                        <input type="text" id="patientName" name="patientName" placeholder="请输入患者姓名">
                    </div>
                    <div class="form-group">
                        <label for="aConstant">A常数</label>
                        <input type="number" id="aConstant" name="aConstant" value="119.30" step="0.01" required>
                        <div class="param-hint">默认值：119.30（可根据晶体类型调整）</div>
                    </div>
                </div>
                
                <div class="form-section">
                    <h2 class="section-title">图片识别（可选）</h2>
                    <div class="form-group">
                        <label for="imageUpload">上传IOL master晶体单图片</label>
                        <input type="file" id="imageUpload" name="imageUpload" accept="image/*" style="margin-bottom: 10px;">
                        <button type="button" id="extractBtn" class="btn" style="background: #28a745; margin-top: 10px;">从图片提取数据</button>
                        <div class="param-hint">支持JPG、PNG等格式，AI将自动识别并填充相关数据</div>
                        <div style="margin-top: 10px; padding: 10px; background: #fff3cd; border: 1px solid #ffc107; border-radius: 5px; font-size: 0.9em; color: #856404;">
                            <strong>⚠️ 注意：</strong>大模型识别不能保证100%准确，建议用户自行确认识别结果后再进行计算。
                        </div>
                    </div>
                    <div id="imagePreview" style="margin-top: 10px; display: none;">
                        <img id="previewImg" style="max-width: 100%; max-height: 200px; border: 1px solid #ddd; border-radius: 5px;">
                    </div>
                </div>
                
                <div class="form-section">
                    <h2 class="section-title">眼部参数</h2>
                    
                    <div class="eye-section" id="rightEyeSection">
                        <div class="eye-header">
                            <input type="checkbox" id="rightEyeEnabled">
                            <label for="rightEyeEnabled">右眼 (OD)</label>
                        </div>
                        <div class="eye-params" id="rightEyeParams">
                            <div class="form-group" style="margin-bottom: 10px;">
                                <div style="display: flex; align-items: center;">
                                    <input type="checkbox" id="rightSiliconeOil" name="rightSiliconeOil" style="width: 13px; margin-right: 8px; transform: scale(1.2);">
                                    <label for="rightSiliconeOil" style="margin: 0; font-weight: normal;">硅油眼</label>
                                </div>
                                <div class="param-hint" style="margin-top: 2px; margin-left: 20px;">*勾选后会使用硅油眼轴校正，如输入结果已经校正则无需勾选。该功能未完善。</div>
                            </div>
                            <div class="form-group">
                                <label for="rightAL">眼轴长度 (AL) mm</label>
                                <input type="number" id="rightAL" name="rightAL" step="0.01" min="12" max="38">
                            </div>
                            <div class="form-group">
                                <label for="rightK1">角膜曲率 K1 D</label>
                                <input type="number" id="rightK1" name="rightK1" step="0.01" min="30" max="60">
                            </div>
                            <div class="form-group">
                                <label for="rightK2">角膜曲率 K2 D</label>
                                <input type="number" id="rightK2" name="rightK2" step="0.01" min="30" max="60">
                            </div>
                            <div class="form-group">
                                <label for="rightACD">ACD mm（可选）</label>
                                <input type="number" id="rightACD" name="rightACD" step="0.01" min="0" max="6" placeholder="默认3.00">
                            </div>
                            <div class="form-group">
                                <label for="rightRefraction">目标屈光度 D（可选）</label>
                                <input type="number" id="rightRefraction" name="rightRefraction" step="0.01" min="-5" max="5" placeholder="默认0.0">
                            </div>
                        </div>
                    </div>
                    
                    <div class="eye-section" id="leftEyeSection">
                        <div class="eye-header">
                            <input type="checkbox" id="leftEyeEnabled">
                            <label for="leftEyeEnabled">左眼 (OS)</label>
                        </div>
                        <div class="eye-params" id="leftEyeParams">
                            <div class="form-group" style="margin-bottom: 10px;">
                                <div style="display: flex; align-items: center;">
                                    <input type="checkbox" id="leftSiliconeOil" name="leftSiliconeOil" style="width: 13px; margin-right: 8px; transform: scale(1.2);">
                                    <label for="leftSiliconeOil" style="margin: 0; font-weight: normal;">硅油眼</label>
                                </div>
                                <div class="param-hint" style="margin-top: 2px; margin-left: 20px;">*勾选后会使用硅油眼轴校正，如输入结果已经校正则无需勾选。该功能未完善。</div>
                            </div>
                            <div class="form-group">
                                <label for="leftAL">眼轴长度 (AL) mm</label>
                                <input type="number" id="leftAL" name="leftAL" step="0.01" min="12" max="38">
                            </div>
                            <div class="form-group">
                                <label for="leftK1">角膜曲率 K1 D</label>
                                <input type="number" id="leftK1" name="leftK1" step="0.01" min="30" max="60">
                            </div>
                            <div class="form-group">
                                <label for="leftK2">角膜曲率 K2 D</label>
                                <input type="number" id="leftK2" name="leftK2" step="0.01" min="30" max="60">
                            </div>
                            <div class="form-group">
                                <label for="leftACD">ACD mm（可选）</label>
                                <input type="number" id="leftACD" name="leftACD" step="0.01" min="0" max="6" placeholder="默认3.00">
                            </div>
                            <div class="form-group">
                                <label for="leftRefraction">目标屈光度 D（可选）</label>
                                <input type="number" id="leftRefraction" name="leftRefraction" step="0.01" min="-5" max="5" placeholder="默认0.0">
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="btn-container">
                    <button type="submit" class="btn" id="calculateBtn" disabled>计算IOL度数</button>
                </div>
            </form>
            
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p>正在计算中，请稍候...</p>
            </div>
            
            <div class="error-message" id="errorMessage"></div>
            
            <div class="results-section" id="resultsSection">
                <h2 class="section-title">计算结果</h2>
                <div id="resultsContent"></div>
            </div>
        </div>
    </div>

    <script>
        // 客户端图片处理器
        class ClientImageProcessor {
            constructor(maxSize = 1024, quality = 1.0) {
                this.maxSize = maxSize;
                this.quality = quality;
            }
            
            // 压缩图片到最长边为maxSize像素
            async compressImage(file) {
                return new Promise((resolve, reject) => {
                    const canvas = document.createElement('canvas');
                    const ctx = canvas.getContext('2d');
                    const img = new Image();
                    
                    img.onload = () => {
                        try {
                            // 计算新的尺寸
                            let { width, height } = img;
                            const maxDimension = Math.max(width, height);
                            
                            if (maxDimension > this.maxSize) {
                                const scale = this.maxSize / maxDimension;
                                width = Math.round(width * scale);
                                height = Math.round(height * scale);
                            }
                            
                            // 设置canvas尺寸
                            canvas.width = width;
                            canvas.height = height;
                            
                            // 绘制压缩后的图片
                            ctx.drawImage(img, 0, 0, width, height);
                            
                            // 转换为blob，然后转换为base64
                            canvas.toBlob((blob) => {
                                const reader = new FileReader();
                                reader.onload = () => {
                                    // 移除data:image/...;base64,前缀
                                    const base64 = reader.result.split(',')[1];
                                    resolve(base64);
                                };
                                reader.onerror = reject;
                                reader.readAsDataURL(blob);
                            }, 'image/jpeg', this.quality);
                        } catch (error) {
                            reject(error);
                        }
                    };
                    
                    img.onerror = reject;
                    img.src = URL.createObjectURL(file);
                });
            }
            
            // 验证图片文件
            validateImageFile(file, maxSize = 10 * 1024 * 1024) {
                // 检查文件类型
                if (!file.type.startsWith('image/')) {
                    return { valid: false, error: '请选择图片文件' };
                }
                
                // 检查文件大小
                if (file.size > maxSize) {
                    return { 
                        valid: false, 
                        error: `图片文件大小不能超过${Math.round(maxSize / (1024 * 1024))}MB` 
                    };
                }
                
                return { valid: true };
            }
            
            // 获取图片信息
            getImageInfo(file) {
                return {
                    name: file.name,
                    size: file.size,
                    sizeMB: Math.round(file.size / (1024 * 1024) * 100) / 100,
                    type: file.type,
                    lastModified: new Date(file.lastModified).toISOString()
                };
            }
            
            // 将文件转换为base64（带压缩）
            async fileToBase64(file) {
                const validation = this.validateImageFile(file);
                if (!validation.valid) {
                    throw new Error(validation.error);
                }
                
                return await this.compressImage(file);
            }
        }

        // 全局实例
        const imageProcessor = new ClientImageProcessor(1024, 1.0);

        const rightEyeEnabled = document.getElementById('rightEyeEnabled');
        const leftEyeEnabled = document.getElementById('leftEyeEnabled');
        const rightEyeParams = document.getElementById('rightEyeParams');
        const leftEyeParams = document.getElementById('leftEyeParams');
        const rightEyeSection = document.getElementById('rightEyeSection');
        const leftEyeSection = document.getElementById('leftEyeSection');
        const calculateBtn = document.getElementById('calculateBtn');

        rightEyeEnabled.addEventListener('change', function() {
            if (this.checked) {
                rightEyeParams.classList.add('show');
                rightEyeSection.classList.add('active');
                // 只设置必需字段为必填，ACD和目标屈光度是可选的
                document.querySelectorAll('#rightAL, #rightK1, #rightK2').forEach(input => input.required = true);
            } else {
                rightEyeParams.classList.remove('show');
                rightEyeSection.classList.remove('active');
                document.querySelectorAll('#rightEyeParams input').forEach(input => input.required = false);
            }
            validateForm();
        });

        leftEyeEnabled.addEventListener('change', function() {
            if (this.checked) {
                leftEyeParams.classList.add('show');
                leftEyeSection.classList.add('active');
                // 只设置必需字段为必填，ACD和目标屈光度是可选的
                document.querySelectorAll('#leftAL, #leftK1, #leftK2').forEach(input => input.required = true);
            } else {
                leftEyeParams.classList.remove('show');
                leftEyeSection.classList.remove('active');
                document.querySelectorAll('#leftEyeParams input').forEach(input => input.required = false);
            }
            validateForm();
        });

        function validateForm() {
            const hasRightEye = rightEyeEnabled.checked && validateEyeParams('right');
            const hasLeftEye = leftEyeEnabled.checked && validateEyeParams('left');
            calculateBtn.disabled = !(hasRightEye || hasLeftEye);
        }

        function validateEyeParams(eye) {
            const al = document.getElementById(eye + 'AL').value;
            const k1 = document.getElementById(eye + 'K1').value;
            const k2 = document.getElementById(eye + 'K2').value;
            return al && k1 && k2 && al > 0 && k1 > 0 && k2 > 0;
        }

        document.querySelectorAll('input').forEach(input => {
            input.addEventListener('input', validateForm);
        });

        // 图片上传和预览功能
        const imageUpload = document.getElementById('imageUpload');
        const imagePreview = document.getElementById('imagePreview');
        const previewImg = document.getElementById('previewImg');
        const extractBtn = document.getElementById('extractBtn');

        imageUpload.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                // 检查文件类型
                if (!file.type.startsWith('image/')) {
                    alert('请选择图片文件');
                    return;
                }

                // 检查文件大小（限制为10MB）
                if (file.size > 10 * 1024 * 1024) {
                    alert('图片文件大小不能超过10MB');
                    return;
                }

                // 预览图片
                const reader = new FileReader();
                reader.onload = function(e) {
                    previewImg.src = e.target.result;
                    imagePreview.style.display = 'block';
                };
                reader.readAsDataURL(file);
            } else {
                imagePreview.style.display = 'none';
            }
        });

        // 从图片提取数据
        extractBtn.addEventListener('click', async function() {
            const file = imageUpload.files[0];
            if (!file) {
                alert('请先选择图片文件');
                return;
            }

            const errorMessage = document.getElementById('errorMessage');
            const loading = document.getElementById('loading');
            const statusContainer = document.getElementById('statusContainer');
            
            // 清除左右眼的识别参数
            clearEyeParameters();
            
            errorMessage.classList.remove('show');
            loading.classList.add('show');
            extractBtn.disabled = true;
            extractBtn.textContent = '正在处理图片...';

            // 创建或更新状态显示区域
            if (!statusContainer) {
                const statusDiv = document.createElement('div');
                statusDiv.id = 'statusContainer';
                statusDiv.style.cssText = `
                    background: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 5px;
                    padding: 15px;
                    margin: 10px 0;
                    font-family: monospace;
                    font-size: 0.9em;
                    max-height: 200px;
                    overflow-y: auto;
                `;
                statusDiv.innerHTML = '<div style="font-weight: bold; margin-bottom: 10px;">处理状态：</div><div id="statusMessages"></div>';
                imageUpload.parentNode.insertBefore(statusDiv, imageUpload.nextSibling);
            }
            
            const statusMessages = document.getElementById('statusMessages');
            statusMessages.innerHTML = '';

            function addStatusMessage(message, type = 'info') {
                const timestamp = new Date().toLocaleTimeString();
                const messageDiv = document.createElement('div');
                messageDiv.style.cssText = `
                    margin: 5px 0;
                    padding: 5px;
                    border-left: 3px solid ${type === 'error' ? '#dc3545' : type === 'success' ? '#28a745' : '#007bff'};
                    background: ${type === 'error' ? '#f8d7da' : type === 'success' ? '#d4edda' : '#e7f3ff'};
                `;
                messageDiv.innerHTML = `<span style="color: #666;">[${timestamp}]</span> ${message}`;
                statusMessages.appendChild(messageDiv);
                statusMessages.scrollTop = statusMessages.scrollHeight;
            }

            try {
                // 在浏览器端压缩图片并转换为base64
                addStatusMessage('开始处理图片...', 'info');
                console.log('开始处理图片...');
                const base64 = await imageProcessor.fileToBase64(file);
                console.log('图片处理完成，大小:', Math.round(base64.length * 0.75 / 1024) + 'KB');
                addStatusMessage(`图片处理完成，大小: ${Math.round(base64.length * 0.75 / 1024)}KB`, 'success');
                
                // 更新按钮文本
                extractBtn.textContent = '正在识别...';
                addStatusMessage('发送到服务器进行识别...', 'info');
                
                // 发送到服务器进行识别
                const response = await fetch('/api', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ image: base64, mode: 'extract-from-image' })
                });

                const result = await response.json();

                // 显示状态历史
                if (result.status_history && result.status_history.length > 0) {
                    addStatusMessage('=== 服务器处理状态 ===', 'info');
                    result.status_history.forEach(status => {
                        addStatusMessage(status.message, 'info');
                    });
                }

                if (response.ok && result.success) {
                    // 显示提取次数信息
                    if (result.total_extractions) {
                        addStatusMessage(`总共进行了 ${result.total_extractions} 次识别`, 'info');
                    }
                    if (result.consensus_reached !== undefined) {
                        addStatusMessage(`多数决结果: ${result.consensus_reached ? '达成共识' : '未达成共识'}`, result.consensus_reached ? 'success' : 'error');
                    }
                    
                    // 填充表单数据
                    // /api 接口（auto process）返回的数据结构中，眼部参数在 extracted_data 里
                    // /api/extract 接口返回的数据结构中，眼部参数直接在 data 里
                    const fillData = (result.data && result.data.extracted_data)
                        ? Object.assign({}, result.data.extracted_data, {
                            patient_name: result.data.patient_name ?? result.data.extracted_data.patient_name,
                            a_constant: result.data.a_constant ?? result.data.extracted_data.a_constant
                          })
                        : result.data;
                    fillFormData(fillData);
                    
                    // 显示成功消息
                    addStatusMessage('数据提取成功，已填充到表单', 'success');
                    errorMessage.textContent = '✓ 数据提取成功，请检查并确认数据准确性';
                    errorMessage.style.background = '#d4edda';
                    errorMessage.style.color = '#155724';
                    errorMessage.style.borderColor = '#c3e6cb';
                    errorMessage.classList.add('show');
                    
                    // 3秒后恢复正常样式
                    setTimeout(() => {
                        errorMessage.classList.remove('show');
                        errorMessage.style.background = '';
                        errorMessage.style.color = '';
                        errorMessage.style.borderColor = '';
                    }, 3000);
                    
                } else if (result.requires_manual_verification) {
                    // 需要手动校验的情况
                    addStatusMessage('识别数据存在差异，需要手动校验', 'warning');
                    
                    // 显示共识详情
                    if (result.consensus_details) {
                        addStatusMessage('=== 共识分析详情 ===', 'info');
                        for (const [field, details] of Object.entries(result.consensus_details)) {
                            if (details.has_consensus) {
                                addStatusMessage(`${field}: 达成共识 (${details.consensus_value})`, 'success');
                            } else {
                                addStatusMessage(`${field}: 未达成共识`, 'warning');
                            }
                        }
                    }
                    
                    // 显示手动校验提示
                    errorMessage.textContent = '⚠️ 识别数据存在错误，请手动校验';
                    errorMessage.style.background = '#fff3cd';
                    errorMessage.style.color = '#856404';
                    errorMessage.style.borderColor = '#ffeaa7';
                    errorMessage.classList.add('show');
                    
                    // 不自动隐藏错误消息，让用户手动校验
                    addStatusMessage('请根据上方识别结果手动填写表单数据', 'warning');
                    
                } else {
                    addStatusMessage(`提取失败: ${result.error || '图片识别失败'}`, 'error');
                    throw new Error(result.error || '图片识别失败');
                }
            } catch (error) {
                addStatusMessage(`处理错误: ${error.message}`, 'error');
                errorMessage.textContent = '图片处理错误：' + error.message;
                errorMessage.style.background = '#f8d7da';
                errorMessage.style.color = '#721c24';
                errorMessage.style.borderColor = '#f5c6cb';
                errorMessage.classList.add('show');
            } finally {
                loading.classList.remove('show');
                extractBtn.disabled = false;
                extractBtn.textContent = '从图片提取数据';
            }
        });

        // 清除左右眼参数的函数
        function clearEyeParameters() {
            // 清除右眼参数
            document.getElementById('rightAL').value = '';
            document.getElementById('rightK1').value = '';
            document.getElementById('rightK2').value = '';
            document.getElementById('rightACD').value = '';
            document.getElementById('rightRefraction').value = '';
            
            // 清除左眼参数
            document.getElementById('leftAL').value = '';
            document.getElementById('leftK1').value = '';
            document.getElementById('leftK2').value = '';
            document.getElementById('leftACD').value = '';
            document.getElementById('leftRefraction').value = '';
            
            // 清除患者姓名和A常数
            document.getElementById('patientName').value = '';
            document.getElementById('aConstant').value = '119.30'; // 恢复默认值
            
            // 取消选中左右眼
            document.getElementById('rightEyeEnabled').checked = false;
            document.getElementById('leftEyeEnabled').checked = false;
            
            // 隐藏眼部参数区域
            document.getElementById('rightEyeParams').classList.remove('show');
            document.getElementById('leftEyeParams').classList.remove('show');
            document.getElementById('rightEyeSection').classList.remove('active');
            document.getElementById('leftEyeSection').classList.remove('active');
            
            // 清除建议框
            removeExistingSuggestion(document.getElementById('rightAL'));
            removeExistingSuggestion(document.getElementById('leftAL'));
            
            // 隐藏结果区域
            document.getElementById('resultsSection').classList.remove('show');
            
            // 验证表单状态
            validateForm();
        }

        // 将文件转换为base64（带压缩）
        function fileToBase64(file) {
            return imageProcessor.fileToBase64(file);
        }

        function roundToTwoDecimals(value) {
            if (value === null || value === undefined || value === '') {
                return null;
            }

            const parsedValue = Number(value);
            if (!Number.isFinite(parsedValue)) {
                return null;
            }

            return Number(parsedValue.toFixed(2));
        }

        function formatToTwoDecimals(value) {
            const roundedValue = roundToTwoDecimals(value);
            if (roundedValue === null) {
                return '';
            }

            return roundedValue.toFixed(2);
        }

        // 填充表单数据
        function fillFormData(data) {
            // 填充患者姓名
            if (data.patient_name) {
                document.getElementById('patientName').value = data.patient_name;
            }

            // 填充A常数
            if (data.a_constant !== null && data.a_constant !== undefined) {
                document.getElementById('aConstant').value = formatToTwoDecimals(data.a_constant);
            }

            // 填充右眼数据
            if (data.right_eye && (data.right_eye.AL || data.right_eye.K1 || data.right_eye.K2)) {
                rightEyeEnabled.checked = true;
                rightEyeEnabled.dispatchEvent(new Event('change'));
                
                if (data.right_eye.AL) document.getElementById('rightAL').value = data.right_eye.AL;
                if (data.right_eye.K1) document.getElementById('rightK1').value = data.right_eye.K1;
                if (data.right_eye.K2) document.getElementById('rightK2').value = data.right_eye.K2;
                if (data.right_eye.ACD !== null && data.right_eye.ACD !== undefined) {
                    document.getElementById('rightACD').value = formatToTwoDecimals(data.right_eye.ACD);
                }
            }

            // 填充左眼数据
            if (data.left_eye && (data.left_eye.AL || data.left_eye.K1 || data.left_eye.K2)) {
                leftEyeEnabled.checked = true;
                leftEyeEnabled.dispatchEvent(new Event('change'));
                
                if (data.left_eye.AL) document.getElementById('leftAL').value = data.left_eye.AL;
                if (data.left_eye.K1) document.getElementById('leftK1').value = data.left_eye.K1;
                if (data.left_eye.K2) document.getElementById('leftK2').value = data.left_eye.K2;
                if (data.left_eye.ACD !== null && data.left_eye.ACD !== undefined) {
                    document.getElementById('leftACD').value = formatToTwoDecimals(data.left_eye.ACD);
                }
            }

            // 验证表单
            validateForm();
            
            // 延迟触发建议显示，确保数据填充完成
            setTimeout(() => {
                triggerSuggestionsAfterFill();
            }, 100);
        }

        // 在数据填充后触发建议显示
        function triggerSuggestionsAfterFill() {
            // 检查右眼
            const rightAL = document.getElementById('rightAL');
            const rightACD = document.getElementById('rightACD');
            if (rightAL.value && rightEyeEnabled.checked) {
                const AL = parseFloat(rightAL.value);
                const ACD = rightACD.value ? parseFloat(rightACD.value) : null;
                const suggestion = generateBarrettSuggestion(AL, ACD);
                showSuggestion(rightAL, suggestion);
            }
            
            // 检查左眼
            const leftAL = document.getElementById('leftAL');
            const leftACD = document.getElementById('leftACD');
            if (leftAL.value && leftEyeEnabled.checked) {
                const AL = parseFloat(leftAL.value);
                const ACD = leftACD.value ? parseFloat(leftACD.value) : null;
                const suggestion = generateBarrettSuggestion(AL, ACD);
                showSuggestion(leftAL, suggestion);
            }
        }

        // 硅油眼矫正函数
        function applySiliconeOilCorrection(eyeData) {
            if (!eyeData || !eyeData.SiliconeOil) {
                return eyeData;
            }
            
            const AL = eyeData.AL;
            const ACD = eyeData.ACD || 3; // 如果ACD未输入，使用默认值3
            
            // 实际眼轴长 = (硅油存在时的眼轴测量长度 - 前房深度) × 990 / 1532 + 前房深度
            const correctedAL = (AL - ACD) * 990 / 1532 + ACD;
            
            // 创建新的眼数据对象，应用矫正
            const correctedEyeData = {
                ...eyeData,
                original_AL: AL, // 保存原始眼轴值
                AL: correctedAL, // 应用矫正后的眼轴
                silicone_correction: correctedAL - AL // 保存矫正值
            };
            
            return correctedEyeData;
        }

        document.getElementById('iolForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const errorMessage = document.getElementById('errorMessage');
            const loading = document.getElementById('loading');
            const resultsSection = document.getElementById('resultsSection');
            
            errorMessage.classList.remove('show');
            resultsSection.classList.remove('show');
            loading.classList.add('show');
            
            try {
                const formData = {
                    patient_name: document.getElementById('patientName').value || null,
                    a_constant: roundToTwoDecimals(
                        document.getElementById('aConstant').value
                    )
                };

                if (rightEyeEnabled.checked) {
                    const rightACDValue = roundToTwoDecimals(
                        document.getElementById('rightACD').value
                    );

                    let rightEyeData = {
                        AL: parseFloat(document.getElementById('rightAL').value),
                        K1: parseFloat(document.getElementById('rightK1').value),
                        K2: parseFloat(document.getElementById('rightK2').value),
                        ACD: rightACDValue === null ? undefined : rightACDValue,
                        Refraction: document.getElementById('rightRefraction').value ? parseFloat(document.getElementById('rightRefraction').value) : undefined,
                        SiliconeOil: document.getElementById('rightSiliconeOil').checked
                    };
                    
                    // 应用硅油眼矫正
                    rightEyeData = applySiliconeOilCorrection(rightEyeData);
                    formData.right_eye = rightEyeData;
                }

                if (leftEyeEnabled.checked) {
                    const leftACDValue = roundToTwoDecimals(
                        document.getElementById('leftACD').value
                    );

                    let leftEyeData = {
                        AL: parseFloat(document.getElementById('leftAL').value),
                        K1: parseFloat(document.getElementById('leftK1').value),
                        K2: parseFloat(document.getElementById('leftK2').value),
                        ACD: leftACDValue === null ? undefined : leftACDValue,
                        Refraction: document.getElementById('leftRefraction').value ? parseFloat(document.getElementById('leftRefraction').value) : undefined,
                        SiliconeOil: document.getElementById('leftSiliconeOil').checked
                    };
                    
                    // 应用硅油眼矫正
                    leftEyeData = applySiliconeOilCorrection(leftEyeData);
                    formData.left_eye = leftEyeData;
                }

                const response = await fetch('/api', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({...formData, mode: 'calculate'})
                });

                const result = await response.json();

                if (response.ok && result.success) {
                    displayResults(result.data);
                } else {
                    throw new Error(result.message || '计算失败');
                }
            } catch (error) {
                errorMessage.textContent = '错误：' + error.message;
                errorMessage.classList.add('show');
            } finally {
                loading.classList.remove('show');
            }
        });

        function displayResults(data) {
            const resultsContent = document.getElementById('resultsContent');
            resultsContent.innerHTML = '';

            let hasValidData = false;

            if (data.right_eye && data.right_eye.iol_options && data.right_eye.iol_options.length > 0) {
                // 获取右眼目标屈光度
                const rightTargetRefraction = document.getElementById('rightRefraction').value ?
                    parseFloat(document.getElementById('rightRefraction').value) : 0;
                resultsContent.appendChild(createResultCard('右眼 (OD)', data.right_eye, rightTargetRefraction));
                hasValidData = true;
            }

            if (data.left_eye && data.left_eye.iol_options && data.left_eye.iol_options.length > 0) {
                // 获取左眼目标屈光度
                const leftTargetRefraction = document.getElementById('leftRefraction').value ?
                    parseFloat(document.getElementById('leftRefraction').value) : 0;
                resultsContent.appendChild(createResultCard('左眼 (OS)', data.left_eye, leftTargetRefraction));
                hasValidData = true;
            }

            if (hasValidData) {
                document.getElementById('resultsSection').classList.add('show');
            } else {
                // 如果没有有效数据，显示提示信息
                resultsContent.innerHTML = '<p style="text-align: center; color: #666; padding: 20px;">暂无计算结果</p>';
                document.getElementById('resultsSection').classList.add('show');
            }
        }

        function createResultCard(title, eyeData, targetRefraction = 0) {
            const card = document.createElement('div');
            card.className = 'result-card';

            // 根据目标屈光度找到最接近的晶体度数
            let closestOption = null;
            let minDiff = Infinity;
            
            // 首先重置所有选项的推荐状态
            eyeData.iol_options.forEach(option => {
                option.recommended = false;
            });
            
            // 找到最接近目标屈光度的选项
            eyeData.iol_options.forEach(option => {
                const refractionValue = parseFloat(option.refraction);
                const diff = Math.abs(refractionValue - targetRefraction);
                if (diff < minDiff) {
                    minDiff = diff;
                    closestOption = option;
                }
            });
            
            // 标记最接近的选项为推荐
            if (closestOption) {
                closestOption.recommended = true;
            }

            let tableHTML = '<h4>' + title + '</h4>';
            tableHTML += '<table class="result-table">';
            tableHTML += '<thead><tr><th>IOL度数</th><th>预期屈光度</th><th>推荐</th></tr></thead><tbody>';

            eyeData.iol_options.forEach(option => {
                const rowClass = option.recommended ? 'recommended' : '';
                tableHTML += '<tr class="' + rowClass + '">';
                tableHTML += '<td>' + option.iol_power + '</td>';
                tableHTML += '<td>' + option.refraction + '</td>';
                tableHTML += '<td>' + (option.recommended ? '✓ 推荐' : '') + '</td>';
                tableHTML += '</tr>';
            });

            tableHTML += '</tbody></table>';

            // 显示推荐信息
            if (closestOption) {
                tableHTML += '<div style="margin-top: 15px; padding: 10px; background: #d4edda; border-radius: 5px;">';
                tableHTML += '<strong>推荐方案：</strong>根据目标屈光度 ' + targetRefraction.toFixed(2) + 'D，';
                tableHTML += '推荐使用 ' + closestOption.iol_power + 'D IOL晶体，';
                tableHTML += '预期屈光度为 ' + closestOption.refraction + 'D';
                tableHTML += '</div>';
            }
            
            // 显示硅油眼矫正信息
            const eye = title.includes('右眼') ? 'right' : 'left';
            const siliconeOilCheckbox = document.getElementById(eye + 'SiliconeOil');
            if (siliconeOilCheckbox && siliconeOilCheckbox.checked) {
                const originalAL = document.getElementById(eye + 'AL').value;
                const ACD = document.getElementById(eye + 'ACD').value || 3;
                const Ns = 1.4034;
                const Nv = 1.336;
                const correction = ((Ns - Nv) / (parseFloat(originalAL) - parseFloat(ACD))) * 1000;
                const correctedAL = parseFloat(originalAL) + correction;
                
                tableHTML += '<div style="margin-top: 10px; padding: 10px; background: #fff3cd; border-radius: 5px;">';
                tableHTML += '<strong>硅油眼矫正信息：</strong><br>';
                tableHTML += '原始眼轴：' + originalAL + 'mm<br>';
                tableHTML += 'ACD：' + formatToTwoDecimals(ACD) + 'mm<br>';
                tableHTML += '矫正值：' + correction.toFixed(4) + 'mm<br>';
                tableHTML += '矫正后眼轴：' + correctedAL.toFixed(4) + 'mm<br>';
                tableHTML += '<small>公式：[(1.4034-1.336) / (AL-ACD)] × 1000</small>';
                tableHTML += '</div>';
            }

            card.innerHTML = tableHTML;
            return card;
        }

        // 生成Barrett公式建议的函数
        function generateBarrettSuggestion(AL, ACD) {
            if (!AL || AL <= 0) return null;
            
            let suggestion = {
                title: "★ Barrett公式建议",
                content: ""
            };
            
            // ★1、短眼轴（AL＜23mm）：主要影响因素为ACD和ELP
            if (AL < 23) {
                if (ACD && ACD > 0) {
                    if (ACD > 3) {
                        // ②前房深度正常偏深（ACD＞3mm）
                        suggestion.content = "短眼轴（AL＜23mm），前房深度正常偏深（ACD＞3mm）：容易远视漂移，目标屈光度比常规多留-0.5D左右";
                    } else if (ACD < 2.6) {
                        // ③前房深度很浅（＜2.6mm）
                        suggestion.content = "短眼轴（AL＜23mm），前房深度很浅（ACD＜2.6mm）：容易近视漂移，目标屈光度比常规少留0.5D左右。";
                    } else {
                        // ①前房深度正常偏浅（3mm＞ACD＞2.6mm）
                        suggestion.content = "短眼轴（AL＜23mm），前房深度正常偏浅（3mm＞ACD＞2.6mm）：目标屈光度按常规留-0.3左右";
                    }
                } else {
                    suggestion.content = "短眼轴（AL＜23mm）：主要影响因素为ACD和ELP，建议输入ACD值获得更精确的建议";
                }
            }
            // ★2、正常眼轴（23mm＜AL＜25mm）
            else if (AL >= 23 && AL < 25) {
                suggestion.content = "正常眼轴（23mm＜AL＜25mm）：目标屈光度按常规留-0.3~-0.5D";
            }
            // ★3、长眼轴（AL＞25mm）：主要影响因素为AL
            else if (AL >= 25) {
                if (AL >= 25 && AL < 26) {
                    // ①眼轴长度尚可（25mm＜AL＜26mm）
                    suggestion.content = "长眼轴（25mm＜AL＜26mm）：目标屈光度常规留-0.5-0.8左右";
                } else if (AL >= 26 && AL < 28) {
                    // ②眼轴长度（26mm＜AL＜28mm）
                    suggestion.content = "长眼轴（26mm＜AL＜28mm）：容易远视漂移，目标屈光度建议留-1.0D~-1.5D左右";
                } else if (AL >= 28 && AL < 30) {
                    // ③眼轴长度（28mm＜AL＜30mm）
                    suggestion.content = "长眼轴（28mm＜AL＜30mm）：容易大度数远视漂移，目标屈光度建议留-1.5D~-2.0D左右";
                } else if (AL >= 30) {
                    // ④⑤眼轴长度（AL＞30mm）
                    suggestion.content = "长眼轴（AL＞30mm）：容易大幅度远视漂移，目标屈光度建议-2.0D~-3.0D，后巩膜葡萄肿严重时建议预留＞-3.0D";
                }
            }
            
            return suggestion.content ? suggestion : null;
        }

        // 显示建议框
        function showSuggestion(inputElement, suggestion) {
            // 移除已存在的建议框
            removeExistingSuggestion(inputElement);
            
            if (!suggestion) return;
            
            // 创建建议框元素
            const suggestionBox = document.createElement('div');
            suggestionBox.className = 'suggestion-box';
            suggestionBox.innerHTML = `
                <div class="suggestion-title">${suggestion.title}</div>
                <div class="suggestion-content">${suggestion.content}</div>
            `;
            
            // 找到目标屈光度输入框
            const eye = inputElement.id.includes('right') ? 'right' : 'left';
            const refractionInput = document.getElementById(eye + 'Refraction');
            const targetFormGroup = refractionInput.closest('.form-group');
            
            // 设置建议框位置 - 在目标屈光度下方显示
            suggestionBox.style.position = 'relative';
            suggestionBox.style.marginTop = '10px';
            suggestionBox.style.width = '100%';
            
            // 添加到目标屈光度的form-group中
            targetFormGroup.appendChild(suggestionBox);
            
            // 不再自动隐藏，持续显示
        }

        // 移除已存在的建议框
        function removeExistingSuggestion(inputElement) {
            const eye = inputElement.id.includes('right') ? 'right' : 'left';
            const refractionInput = document.getElementById(eye + 'Refraction');
            const targetFormGroup = refractionInput.closest('.form-group');
            const existingSuggestion = targetFormGroup.querySelector('.suggestion-box');
            if (existingSuggestion) {
                existingSuggestion.parentNode.removeChild(existingSuggestion);
            }
        }

        // 为眼轴长度输入框添加事件监听器
        function setupSuggestionListeners() {
            // 右眼眼轴长度
            const rightAL = document.getElementById('rightAL');
            const rightACD = document.getElementById('rightACD');
            
            rightAL.addEventListener('input', function() {
                const AL = parseFloat(this.value);
                const ACD = rightACD.value ? parseFloat(rightACD.value) : null;
                const suggestion = generateBarrettSuggestion(AL, ACD);
                showSuggestion(this, suggestion);
            });
            
            // 右眼ACD变化时也更新建议
            rightACD.addEventListener('input', function() {
                const AL = rightAL.value ? parseFloat(rightAL.value) : null;
                const ACD = parseFloat(this.value);
                if (AL) {
                    const suggestion = generateBarrettSuggestion(AL, ACD);
                    showSuggestion(rightAL, suggestion);
                }
            });
            
            // 左眼眼轴长度
            const leftAL = document.getElementById('leftAL');
            const leftACD = document.getElementById('leftACD');
            
            leftAL.addEventListener('input', function() {
                const AL = parseFloat(this.value);
                const ACD = leftACD.value ? parseFloat(leftACD.value) : null;
                const suggestion = generateBarrettSuggestion(AL, ACD);
                showSuggestion(this, suggestion);
            });
            
            // 左眼ACD变化时也更新建议
            leftACD.addEventListener('input', function() {
                const AL = leftAL.value ? parseFloat(leftAL.value) : null;
                const ACD = parseFloat(this.value);
                if (AL) {
                    const suggestion = generateBarrettSuggestion(AL, ACD);
                    showSuggestion(leftAL, suggestion);
                }
            });
        }

        // 页面加载完成后设置事件监听器
        document.addEventListener('DOMContentLoaded', function() {
            setupSuggestionListeners();
        });
    </script>
</body>
</html>
"""


def get_webui_page():
    """返回Web UI的HTML页面"""
    return INDEX_PAGE
