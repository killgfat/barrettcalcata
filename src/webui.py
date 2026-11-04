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
        .mode-switch-band { padding: 16px 30px 0; background: white; }
        .mode-switch { display: flex; gap: 4px; max-width: 420px; margin: 0 auto; padding: 4px; border: 1px solid #cbd5e1; border-radius: 8px; background: #f1f5f9; }
        .formula-switch { display: flex; flex-wrap: wrap; gap: 4px; max-width: 820px; margin: 12px auto 0; padding: 4px; border: 1px solid #cbd5e1; border-radius: 8px; background: #f1f5f9; }
        .formula-button { flex: 1 1 160px; min-height: 40px; border: 0; border-radius: 6px; background: transparent; color: #475569; font-size: 14px; font-weight: bold; cursor: pointer; transition: background 0.2s, color 0.2s, box-shadow 0.2s; }
        .formula-button:hover { color: #0f172a; }
        .formula-button.active { background: white; color: #0f766e; box-shadow: 0 1px 4px rgba(15, 23, 42, 0.14); }
        .execution-mode-row { display: flex; align-items: center; justify-content: center; gap: 10px; margin: 10px auto 0; }
        .execution-mode-label { font-weight: bold; color: #475569; font-size: 14px; white-space: nowrap; }
        .execution-mode-state { min-width: 32px; color: #475569; font-size: 14px; font-weight: bold; }
        .toggle-switch { position: relative; width: 58px; height: 32px; padding: 0; border: 2px solid #3f3f46; border-radius: 999px; background: #fff; cursor: pointer; transition: background 0.2s, border-color 0.2s; }
        .toggle-switch .toggle-knob { position: absolute; top: 50%; left: 4px; width: 22px; height: 22px; border-radius: 50%; background: #6b7280; transform: translateY(-50%); transition: left 0.2s, background 0.2s; }
        .toggle-switch[aria-checked="true"] { background: #2f8cff; border-color: #2f8cff; }
        .toggle-switch[aria-checked="true"] .toggle-knob { left: 30px; background: #fff; }
        .toggle-switch:focus-visible { outline: 3px solid rgba(47, 140, 255, 0.35); outline-offset: 2px; }
        .mode-switch-hint { max-width: 720px; margin: 8px auto 0; text-align: center; }
        .formula-summary { margin-bottom: 15px; padding: 10px 14px; border: 1px solid #cbd5e1; border-radius: 8px; background: #f1f5f9; color: #0f172a; font-size: 0.95em; white-space: pre-line; line-height: 1.55; }
        .formula-input-hint { max-width: 760px; margin: 6px auto 0; text-align: center; }
        .haigis-constants { display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: 8px; margin-top: 8px; }
        .haigis-constants-label { color: #475569; font-size: 14px; font-weight: bold; }
        .haigis-constants input { width: 88px; padding: 6px 8px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px; }
        .haigis-constant-field { display: flex; align-items: center; gap: 4px; color: #475569; font-size: 14px; }
        .haigis-constants-note { color: #64748b; font-size: 12px; }
        .mode-button { flex: 1; min-height: 44px; border: 0; border-radius: 6px; background: transparent; color: #475569; font-size: 15px; font-weight: bold; cursor: pointer; transition: background 0.2s, color 0.2s, box-shadow 0.2s; }
        .mode-button:hover { color: #0f172a; }
        .mode-button.active { background: white; color: #0f766e; box-shadow: 0 1px 4px rgba(15, 23, 42, 0.14); }
        [hidden] { display: none !important; }
        .form-section { margin-bottom: 30px; padding: 20px; border: 1px solid #ddd; border-radius: 8px; }
        .section-title { font-size: 1.5em; margin-bottom: 15px; color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: bold; color: #555; }
        .form-group input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; font-size: 16px; }
        .form-group input:focus { outline: none; border-color: #007bff; box-shadow: 0 0 5px rgba(0,123,255,0.3); }
        .form-group select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; font-size: 16px; background: #fff; }
        .form-group select:focus { outline: none; border-color: #007bff; box-shadow: 0 0 5px rgba(0,123,255,0.3); }
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
        .toric-section { border-color: #0f766e; }
        .toric-section .section-title { border-bottom-color: #0f766e; }
        .toric-eye-params { display: none; }
        .toric-eye-params.show { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; }
        .toric-form-note { margin-bottom: 18px; line-height: 1.6; }
        .toric-haigis-fields { grid-column: 1 / -1; min-width: 0; padding: 18px 0 0; border: 0; border-top: 1px solid #cbd5e1; }
        .toric-haigis-fields legend { padding-right: 10px; font-weight: bold; color: #115e59; }
        .toric-extra-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
        .toric-pca-hint { align-self: center; line-height: 1.6; }
        .toric-validation { line-height: 1.6; color: #9f1239; }
        .toric-table-scroll { max-width: 100%; overflow-x: auto; }
        .toric-result-details { line-height: 1.8; overflow-wrap: anywhere; }
        .toric-result-details dt { font-weight: bold; margin-top: 10px; }
        .toric-result-details dd { margin: 0; }
        .formula-button:focus-visible, .mode-button:focus-visible { outline: 2px solid #0f766e; outline-offset: 2px; }
        @media (max-width: 600px) {
            .toric-eye-params.show, .toric-extra-grid { grid-template-columns: minmax(0, 1fr); }
            .toric-section { padding: 14px; }
            .toric-section .eye-section { padding: 12px; }
            .toric-section .form-group, .toric-haigis-fields { min-width: 0; }
        }
        .axis-result { margin-top: 20px; padding: 16px; border: 1px solid #99f6e4; border-radius: 8px; background: #f0fdfa; }
        .axis-result h5 { margin-bottom: 12px; color: #115e59; font-size: 1.05em; }
        .axis-layout { display: grid; grid-template-columns: minmax(220px, 360px) 1fr; gap: 20px; align-items: center; }
        .axis-figure { position: relative; width: 100%; max-width: 360px; aspect-ratio: 1; overflow: hidden; border-radius: 50%; background: #e6fffb; }
        .axis-figure img { display: block; width: 100%; height: 100%; object-fit: cover; }
        .axis-line { position: absolute; left: 10%; top: calc(50% - 0.5px); width: 80%; height: 1px; transform-origin: 50% 50%; background: #16a34a; }
        .axis-legend { display: grid; gap: 8px; font-size: 0.95em; color: #334155; }
        .axis-legend-row { display: flex; justify-content: space-between; gap: 16px; border-bottom: 1px solid #ccfbf1; padding-bottom: 6px; }
        .axis-legend-row strong { color: #0f172a; }
        @media (max-width: 768px) { .axis-layout { grid-template-columns: 1fr; } .axis-figure { margin: 0 auto; } }
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
        .ulib-combobox { position: relative; }
        .ulib-model-list {
            position: absolute; left: 0; right: 0; top: calc(100% + 4px);
            z-index: 60; max-height: 264px; overflow-y: auto;
            margin: 0; padding: 4px 0; list-style: none;
            background: #fff; border: 1px solid #cbd5e1; border-radius: 8px;
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.14);
        }
        .ulib-model-list[hidden] { display: none; }
        .ulib-model-item {
            padding: 8px 12px; font-size: 15px; color: #1e293b;
            cursor: pointer; white-space: nowrap; overflow: hidden;
            text-overflow: ellipsis;
        }
        .ulib-model-item:hover, .ulib-model-item.is-active { background: #eff6ff; }
        .ulib-model-empty { padding: 10px 12px; font-size: 14px; color: #94a3b8; }
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

        <div class="mode-switch-band" aria-label="计算模式">
            <div class="mode-switch" role="group" aria-label="散光模式">
                <button type="button" class="mode-button active" id="sphericalModeButton" aria-pressed="true">非散光</button>
                <button type="button" class="mode-button" id="toricModeButton" aria-pressed="false">散光</button>
            </div>
            <div class="formula-switch" id="formulaSwitch" role="group" aria-label="计算公式">
                <button type="button" class="formula-button active" data-formula="barrett" aria-pressed="true">Barrett Universal II</button>
                <button type="button" class="formula-button" data-formula="hoffer_q" aria-pressed="false">Hoffer Q</button>
                <button type="button" class="formula-button" data-formula="srkt" aria-pressed="false">SRK/T</button>
                <button type="button" class="formula-button" data-formula="haigis" aria-pressed="false">Haigis</button>
            </div>
            <div class="formula-switch" id="toricFormulaSwitch" role="group" aria-label="散光计算公式" hidden>
                <button type="button" class="formula-button active" data-toric-formula="barrett" aria-pressed="true">Barrett Toric · 在线</button>
                <button type="button" class="formula-button" data-toric-formula="haigis-toric" aria-pressed="false">Haigis-T · 本地</button>
            </div>
            <div id="toricFormulaHint" class="param-hint formula-input-hint" hidden></div>
            <div class="execution-mode-row" id="executionModeControls">
                <span class="execution-mode-label">执行方式</span>
                <button type="button" class="toggle-switch" id="executionModeSwitch" role="switch" aria-checked="true" aria-label="切换在线或本地执行">
                    <span class="toggle-knob"></span>
                </button>
                <span class="execution-mode-state" id="executionModeState">在线</span>
            </div>
            <div id="executionModeHint" class="param-hint mode-switch-hint"></div>
            <div id="formulaInputHint" class="param-hint formula-input-hint"></div>
            <div class="haigis-constants" id="haigisConstants" hidden>
                <span class="haigis-constants-label">Haigis 常数</span>
                <label class="haigis-constant-field" for="haigisA0">a0 <input type="number" id="haigisA0" aria-label="Haigis a0" min="-10" max="10" step="0.001" placeholder="a0"></label>
                <label class="haigis-constant-field" for="haigisA1">a1 <input type="number" id="haigisA1" aria-label="Haigis a1" min="-2" max="2" step="0.001" placeholder="a1"></label>
                <label class="haigis-constant-field" for="haigisA2">a2 <input type="number" id="haigisA2" aria-label="Haigis a2" min="-1" max="1" step="0.001" placeholder="a2"></label>
                <span class="haigis-constants-note" id="haigisConstantsNote">照抄 IOL Master 的 a0/a1/a2；不填则用 A 常数近似</span>
            </div>
            <div class="haigis-constants" id="hofferQPacdControls" hidden>
                <label class="haigis-constants-label" for="hofferQPacd">Hoffer Q pACD</label>
                <input type="number" id="hofferQPacd" step="0.01" min="0" max="8" placeholder="留空由 A 常数推导">
                <span class="haigis-constants-note">单位 mm；这是公式常数，不是术前 ACD</span>
            </div>
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
                        <label for="iolModel">晶体型号</label>
                        <div id="barrettModelGroup">
                            <select id="iolModel" name="iolModel">
                                <option value="Personal Constant">Personal Constant（自定义A常数）</option>
                            </select>
                            <div class="param-hint" id="iolModelHint">选择晶体型号可自动填充A常数</div>
                        </div>
                        <div id="ulibModelGroup" hidden>
                            <div class="ulib-combobox">
                                <input type="text" id="ulibModelSearch" placeholder="选择晶体或输入关键词搜索" autocomplete="off" role="combobox" aria-expanded="false" aria-controls="ulibModelList" aria-autocomplete="list">
                                <ul id="ulibModelList" class="ulib-model-list" role="listbox" hidden></ul>
                            </div>
                            <div class="param-hint" id="ulibModelHint">源自 ULIB Constants（2016-10-31）</div>
                        </div>
                    </div>
                    <div class="form-group" id="aConstantGroup">
                        <label for="aConstant">A常数</label>
                        <input type="number" id="aConstant" name="aConstant" value="119.30" step="0.01" required>
                        <div class="param-hint" id="aConstantHint">默认值：119.30（可根据晶体类型调整）</div>
                    </div>
                    <div class="form-group">
                        <label for="kIndex">K-index</label>
                        <select id="kIndex" name="kIndex">
                            <option value="1.3375" selected>1.3375</option>
                            <option value="1.332">1.332</option>
                        </select>
                        <div class="param-hint">选择角膜测量使用的 K-index</div>
                    </div>
                </div>
                
                <div class="form-section" id="imageRecognitionSection">
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
                
                <div class="form-section" id="sphericalEyeSection">
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
                                <input type="number" id="rightACD" name="rightACD" step="0.01" min="0.5" max="8" placeholder="留空由公式决定">
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
                                <input type="number" id="leftACD" name="leftACD" step="0.01" min="0.5" max="8" placeholder="留空由公式决定">
                            </div>
                            <div class="form-group">
                                <label for="leftRefraction">目标屈光度 D（可选）</label>
                                <input type="number" id="leftRefraction" name="leftRefraction" step="0.01" min="-5" max="5" placeholder="默认0.0">
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="btn-container" id="sphericalCalculateContainer">
                    <button type="submit" class="btn" id="calculateBtn" disabled>计算IOL度数</button>
                </div>
            </form>

            <section class="form-section toric-section" id="toricSection" hidden>
                <h2 class="section-title" id="toricSectionTitle">Barrett Universal II 散光晶体</h2>
                <p class="param-hint toric-form-note" id="toricInputHint">使用上方患者、晶体型号、A 常数和 K-index 设置；请至少启用一眼。标有 * 的参数必填。</p>
                <div class="form-group" data-toric-only="barrett" style="max-width: 260px;">
                    <label for="toricCylinderMode">散光符号</label>
                    <select id="toricCylinderMode" name="toricCylinderMode">
                        <option value="-ve" selected>负柱镜（-ve Cylinder）</option>
                        <option value="+ve">正柱镜（+ve Cylinder）</option>
                    </select>
                </div>

                <div class="eye-section" id="toricRightEyeSection">
                    <div class="eye-header">
                        <input type="checkbox" id="toricRightEyeEnabled">
                        <label for="toricRightEyeEnabled">右眼 (OD)</label>
                    </div>
                    <div class="toric-eye-params" id="toricRightEyeParams">
                        <div class="form-group"><label for="toricRightAL">眼轴长度 (AL) mm *</label><input type="number" id="toricRightAL" step="0.01" min="12" max="38"></div>
                        <div class="form-group"><label for="toricRightFlatK">角膜曲率 K1 D *</label><input type="number" id="toricRightFlatK" step="0.01" min="30" max="60"></div>
                        <div class="form-group"><label for="toricRightFlatAxis">K1 轴位 ° *</label><input type="number" id="toricRightFlatAxis" step="any" min="0" max="180"></div>
                        <div class="form-group"><label for="toricRightSteepK">角膜曲率 K2 D *</label><input type="number" id="toricRightSteepK" step="0.01" min="30" max="60"></div>
                        <div class="form-group"><label for="toricRightSteepAxis">K2 轴位 ° *</label><input type="number" id="toricRightSteepAxis" step="any" min="0" max="180"></div>
                        <div class="form-group" data-toric-only="barrett"><label for="toricRightACD">ACD mm（可选）</label><input type="number" id="toricRightACD" value="3.00" step="0.01" min="0" max="6"></div>
                        <div class="form-group" data-toric-only="haigis-toric" hidden><label for="toricRightMeasuredACD">术前实测 ACD (mm) *</label><input type="number" id="toricRightMeasuredACD" step="0.01" min="0.5" max="8" placeholder="填写实测值，不使用默认 ACD"></div>
                        <div class="form-group"><label for="toricRightRefraction">目标屈光度 D（可选）</label><input type="number" id="toricRightRefraction" value="0" step="0.01"></div>
                        <div class="form-group"><label for="toricRightSIA">切口 SIA (D)</label><input type="number" id="toricRightSIA" value="0" step="0.01" min="0" max="2"></div>
                        <div class="form-group" data-toric-only="haigis-toric" hidden><label for="toricRightHaigisIncision">切口位置 (°；SIA 非零时必填)</label><input type="number" id="toricRightHaigisIncision" step="any" min="0" max="360" placeholder="填写实际切口位置"></div>
                        <div class="form-group" data-toric-only="barrett"><label for="toricRightIncision">切口位置 (°)</label><input type="number" id="toricRightIncision" value="135" step="1" min="0" max="360"></div>
                        <fieldset class="toric-haigis-fields" data-toric-only="haigis-toric" hidden>
                            <legend>Haigis-T 散光参数</legend>
                            <div class="toric-extra-grid">
                                <div class="form-group"><label for="toricRightPosteriorMode">后表面散光 / 总散光</label><select id="toricRightPosteriorMode"><option value="none">不计入 PCA</option><option value="measured">实测后表面散光</option><option value="total">实测总散光（TK / TCRP）</option><option value="estimated">估算 PCA（未验证）</option></select></div>
                                <p class="param-hint toric-pca-hint" id="toricRightPosteriorHint"></p>
                                <div class="form-group" data-posterior-mode="measured" hidden><label for="toricRightPosteriorCylinder">后表面光学散光 (D) *</label><input type="number" id="toricRightPosteriorCylinder" step="0.01" min="0"><div class="param-hint">角膜平面非负量值；使用光学强子午线，非后表面曲率陡轴。</div></div>
                                <div class="form-group" data-posterior-mode="measured" hidden><label for="toricRightPosteriorAxis">后表面光学强子午线 (°) *</label><input type="number" id="toricRightPosteriorAxis" step="any" min="0" max="180"></div>
                                <div class="form-group" data-posterior-mode="total" hidden><label for="toricRightTotalSource">总散光来源 *</label><select id="toricRightTotalSource"><option value="TK">TK</option><option value="TCRP">TCRP</option></select></div>
                                <div class="form-group" data-posterior-mode="total" hidden><label for="toricRightTotalCylinder">总散光 (D) *</label><input type="number" id="toricRightTotalCylinder" step="0.01" min="0"></div>
                                <div class="form-group" data-posterior-mode="total" hidden><label for="toricRightTotalAxis">总散光光学强子午线 (°) *</label><input type="number" id="toricRightTotalAxis" step="any" min="0" max="180"></div>
                                <div class="form-group"><label for="toricRightIolCylinder">拟植入 IOL 柱镜 (D)</label><input type="number" id="toricRightIolCylinder" value="0" step="0.01" min="0"><div class="param-hint">IOL 平面非负量值；默认 0 表示尚未矫正，用于残余预测。</div></div>
                                <div class="form-group"><label for="toricRightIolAxis">拟植入轴位 (°)</label><input type="number" id="toricRightIolAxis" step="any" min="0" max="180"><div class="param-hint">IOL 光学弱子午线对齐方向；柱镜非零时必填。</div></div>
                                <div class="form-group"><label for="toricRightIolSE">拟植入 IOL 球镜等效 SE (D)</label><input type="number" id="toricRightIolSE" step="0.01" min="-10" max="45" placeholder="留空使用 Haigis 推荐 SE"></div>
                                <div class="form-group"><label for="toricRightCylinderPowers">可供 IOL 柱镜档位 (D)</label><input type="text" id="toricRightCylinderPowers" placeholder="例如：0, 1.5, 2.25, 3"><div class="param-hint">填写实际可供的 IOL 平面档位，用逗号分隔；留空只给连续解。</div></div>
                            </div>
                        </fieldset>
                        <div class="form-group" data-toric-only="barrett"><label for="toricRightLT">晶体厚度 LT (mm) *</label><input type="number" id="toricRightLT" step="0.01" min="2" max="8"></div>
                        <div class="form-group" data-toric-only="barrett"><label for="toricRightWTW">WTW (mm) *</label><input type="number" id="toricRightWTW" step="0.01" min="8" max="14"></div>
                    </div>
                </div>

                <div class="eye-section" id="toricLeftEyeSection">
                    <div class="eye-header">
                        <input type="checkbox" id="toricLeftEyeEnabled">
                        <label for="toricLeftEyeEnabled">左眼 (OS)</label>
                    </div>
                    <div class="toric-eye-params" id="toricLeftEyeParams">
                        <div class="form-group"><label for="toricLeftAL">眼轴长度 (AL) mm *</label><input type="number" id="toricLeftAL" step="0.01" min="12" max="38"></div>
                        <div class="form-group"><label for="toricLeftFlatK">角膜曲率 K1 D *</label><input type="number" id="toricLeftFlatK" step="0.01" min="30" max="60"></div>
                        <div class="form-group"><label for="toricLeftFlatAxis">K1 轴位 ° *</label><input type="number" id="toricLeftFlatAxis" step="any" min="0" max="180"></div>
                        <div class="form-group"><label for="toricLeftSteepK">角膜曲率 K2 D *</label><input type="number" id="toricLeftSteepK" step="0.01" min="30" max="60"></div>
                        <div class="form-group"><label for="toricLeftSteepAxis">K2 轴位 ° *</label><input type="number" id="toricLeftSteepAxis" step="any" min="0" max="180"></div>
                        <div class="form-group" data-toric-only="barrett"><label for="toricLeftACD">ACD mm（可选）</label><input type="number" id="toricLeftACD" value="3.00" step="0.01" min="0" max="6"></div>
                        <div class="form-group" data-toric-only="haigis-toric" hidden><label for="toricLeftMeasuredACD">术前实测 ACD (mm) *</label><input type="number" id="toricLeftMeasuredACD" step="0.01" min="0.5" max="8" placeholder="填写实测值，不使用默认 ACD"></div>
                        <div class="form-group"><label for="toricLeftRefraction">目标屈光度 D（可选）</label><input type="number" id="toricLeftRefraction" value="0" step="0.01"></div>
                        <div class="form-group"><label for="toricLeftSIA">切口 SIA (D)</label><input type="number" id="toricLeftSIA" value="0" step="0.01" min="0" max="2"></div>
                        <div class="form-group" data-toric-only="haigis-toric" hidden><label for="toricLeftHaigisIncision">切口位置 (°；SIA 非零时必填)</label><input type="number" id="toricLeftHaigisIncision" step="any" min="0" max="360" placeholder="填写实际切口位置"></div>
                        <div class="form-group" data-toric-only="barrett"><label for="toricLeftIncision">切口位置 (°)</label><input type="number" id="toricLeftIncision" value="135" step="1" min="0" max="360"></div>
                        <fieldset class="toric-haigis-fields" data-toric-only="haigis-toric" hidden>
                            <legend>Haigis-T 散光参数</legend>
                            <div class="toric-extra-grid">
                                <div class="form-group"><label for="toricLeftPosteriorMode">后表面散光 / 总散光</label><select id="toricLeftPosteriorMode"><option value="none">不计入 PCA</option><option value="measured">实测后表面散光</option><option value="total">实测总散光（TK / TCRP）</option><option value="estimated">估算 PCA（未验证）</option></select></div>
                                <p class="param-hint toric-pca-hint" id="toricLeftPosteriorHint"></p>
                                <div class="form-group" data-posterior-mode="measured" hidden><label for="toricLeftPosteriorCylinder">后表面光学散光 (D) *</label><input type="number" id="toricLeftPosteriorCylinder" step="0.01" min="0"><div class="param-hint">角膜平面非负量值；使用光学强子午线，非后表面曲率陡轴。</div></div>
                                <div class="form-group" data-posterior-mode="measured" hidden><label for="toricLeftPosteriorAxis">后表面光学强子午线 (°) *</label><input type="number" id="toricLeftPosteriorAxis" step="any" min="0" max="180"></div>
                                <div class="form-group" data-posterior-mode="total" hidden><label for="toricLeftTotalSource">总散光来源 *</label><select id="toricLeftTotalSource"><option value="TK">TK</option><option value="TCRP">TCRP</option></select></div>
                                <div class="form-group" data-posterior-mode="total" hidden><label for="toricLeftTotalCylinder">总散光 (D) *</label><input type="number" id="toricLeftTotalCylinder" step="0.01" min="0"></div>
                                <div class="form-group" data-posterior-mode="total" hidden><label for="toricLeftTotalAxis">总散光光学强子午线 (°) *</label><input type="number" id="toricLeftTotalAxis" step="any" min="0" max="180"></div>
                                <div class="form-group"><label for="toricLeftIolCylinder">拟植入 IOL 柱镜 (D)</label><input type="number" id="toricLeftIolCylinder" value="0" step="0.01" min="0"><div class="param-hint">IOL 平面非负量值；默认 0 表示尚未矫正，用于残余预测。</div></div>
                                <div class="form-group"><label for="toricLeftIolAxis">拟植入轴位 (°)</label><input type="number" id="toricLeftIolAxis" step="any" min="0" max="180"><div class="param-hint">IOL 光学弱子午线对齐方向；柱镜非零时必填。</div></div>
                                <div class="form-group"><label for="toricLeftIolSE">拟植入 IOL 球镜等效 SE (D)</label><input type="number" id="toricLeftIolSE" step="0.01" min="-10" max="45" placeholder="留空使用 Haigis 推荐 SE"></div>
                                <div class="form-group"><label for="toricLeftCylinderPowers">可供 IOL 柱镜档位 (D)</label><input type="text" id="toricLeftCylinderPowers" placeholder="例如：0, 1.5, 2.25, 3"><div class="param-hint">填写实际可供的 IOL 平面档位，用逗号分隔；留空只给连续解。</div></div>
                            </div>
                        </fieldset>
                        <div class="form-group" data-toric-only="barrett"><label for="toricLeftLT">晶体厚度 LT (mm) *</label><input type="number" id="toricLeftLT" step="0.01" min="2" max="8"></div>
                        <div class="form-group" data-toric-only="barrett"><label for="toricLeftWTW">WTW (mm) *</label><input type="number" id="toricLeftWTW" step="0.01" min="8" max="14"></div>
                    </div>
                </div>
                <div class="btn-container">
                    <p class="param-hint toric-validation" id="toricValidationHint" aria-live="polite"></p>
                    <button type="button" class="btn" id="toricCalculateBtn" style="background: #0f766e;" disabled>计算散光晶体</button>
                </div>
            </section>

            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p>正在计算中，请稍候...</p>
            </div>
            
            <div class="error-message" id="errorMessage"></div>
            
            <div class="results-section" id="resultsSection">
                <h2 class="section-title">计算结果</h2>
                <div id="resultsContent"></div>
            </div>

            <div class="results-section" id="toricResultsSection" hidden>
                <h2 class="section-title">散光计算结果与轴位</h2>
                <div id="toricResultsContent"></div>
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

        // IOL晶体型号同步
        const iolModelSelect = document.getElementById('iolModel');
        const aConstantInput = document.getElementById('aConstant');

        async function loadIolModels() {
            try {
                const response = await fetch('/api/iol-models');
                const result = await response.json();
                if (result.success && result.data.models) {
                    result.data.models.forEach(model => {
                        const option = document.createElement('option');
                        option.value = model;
                        option.textContent = model;
                        iolModelSelect.appendChild(option);
                    });
                }
            } catch (e) {
                console.warn('加载晶体型号列表失败:', e);
            }
        }

        iolModelSelect.addEventListener('change', async function() {
            const selected = this.value;
            if (selected === 'Personal Constant') {
                // 自定义常数不是内置的任何一款晶体：解除型号锁定，
                // 保留用户已经填过的值，只在空值时补默认。
                clearUlibConstants();
                resetAConstantToDefault();
                document.getElementById('iolModelHint').textContent =
                    '选择晶体型号可自动填充A常数';
                ulibModelSearch.value = '';
                selectedUlibModelName = '';
                validateToricForm();
                return;
            }

            // 先不动输入框里的值，拿到官网常数后再覆盖；请求失败时用户
            // 原来填的常数仍然在。
            aConstantInput.readOnly = true;
            document.getElementById('iolModelHint').textContent = '正在获取常数...';

            try {
                const response = await fetch(
                    '/api/iol-models?model=' + encodeURIComponent(selected)
                );
                const result = await response.json();
                if (result.success) {
                    const data = result.data;
                    if (data.a_constant !== null && data.a_constant !== undefined) {
                        aConstantInput.value = data.a_constant.toFixed(2);
                    } else {
                        aConstantInput.readOnly = false;
                    }
                    const lf = data.lens_factor;
                    document.getElementById('aConstantHint').textContent =
                        'Lens Factor: ' +
                        (lf !== null && lf !== undefined ? lf : 'N/A');
                    if (data.source === 'ulib') {
                        // Barrett 走自己的 Lens Factor 路径，Haigis/Hoffer Q
                        // 常数与它无关，这里不回填，避免看起来像已生效。
                        let hint = 'ULIB ' + data.source_revision +
                            '（n=' + data.samples + '）';
                        if (data.preliminary) {
                            hint += ' · 样本量偏小，仅供参考';
                        }
                        document.getElementById('iolModelHint').textContent = hint;
                    } else {
                        document.getElementById('iolModelHint').textContent =
                            '已从Barrett官方同步';
                    }
                } else {
                    throw new Error(result.message);
                }
            } catch (e) {
                aConstantInput.readOnly = false;
                document.getElementById('iolModelHint').textContent =
                    '获取失败，请手动输入常数';
            } finally {
                validateToricForm();
            }
            if (!aConstantInput.value) aConstantInput.readOnly = false;
        });

        const FORMULA_CONSTANT_FIELDS = {
            haigisA0: 'a0',
            haigisA1: 'a1',
            haigisA2: 'a2',
            hofferQPacd: '留空由 A 常数推导'
        };

        function clearUlibConstants() {
            // 只解除锁定，保留用户已经填过的值（切换到自定义常数时用）。
            Object.entries(FORMULA_CONSTANT_FIELDS).forEach(([id, placeholder]) => {
                const input = document.getElementById(id);
                if (!input) return;
                input.disabled = false;
                input.placeholder = placeholder;
            });
            aConstantInput.readOnly = false;
        }

        function lockUlibConstants() {
            // 型号已声明时常数由后端查表：输入框锁定但保留原值，
            // 用户能看到自己填过什么，提交时这些字段不会被发送。
            Object.entries(FORMULA_CONSTANT_FIELDS).forEach(([id]) => {
                const input = document.getElementById(id);
                if (!input) return;
                input.disabled = true;
                input.placeholder = '由所选型号决定';
            });
            aConstantInput.readOnly = true;
        }

        loadIolModels();

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
                const response = await fetch('/api/extract', {
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
                        addStatusMessage(`多数决结果: ${result.consensus_reached ? '全部达成共识' : '部分字段未达成共识'}`, result.consensus_reached ? 'success' : 'warning');
                    }
                    
                    // 填充表单数据（仅填充达成共识的字段，未达成共识的为null不会填入）
                    // /api 接口（auto process）返回的数据结构中，眼部参数在 extracted_data 里
                    // /api/extract 接口返回的数据结构中，眼部参数直接在 data 里
                    const fillData = (result.data && result.data.extracted_data)
                        ? Object.assign({}, result.data.extracted_data, {
                            patient_name: result.data.patient_name ?? result.data.extracted_data.patient_name,
                            a_constant: result.data.a_constant ?? result.data.extracted_data.a_constant,
                            haigis_constants: result.data.haigis_constants ?? result.data.extracted_data.haigis_constants,
                            hoffer_q_pacd: result.data.hoffer_q_pacd ?? result.data.extracted_data.hoffer_q_pacd
                          })
                        : result.data;
                    fillFormData(fillData);
                    
                    if (result.requires_manual_verification && result.failed_fields && result.failed_fields.length > 0) {
                        // 部分字段未达成共识，提示用户手动校验
                        addStatusMessage('=== 未达成共识的字段 ===', 'warning');
                        result.failed_fields.forEach(field => {
                            addStatusMessage(`${field}: 三次识别结果不一致，请手动校验`, 'warning');
                        });
                        addStatusMessage('已填充的字段为达成共识的数据，未填充的字段需要手动输入', 'info');
                        
                        errorMessage.textContent = '⚠️ 部分字段未达成共识（' + result.failed_fields.join(', ') + '），请手动校验';
                        errorMessage.style.background = '#fff3cd';
                        errorMessage.style.color = '#856404';
                        errorMessage.style.borderColor = '#ffeaa7';
                        errorMessage.classList.add('show');
                    } else {
                        // 全部达成共识
                        addStatusMessage('数据提取成功，已填充到表单', 'success');
                        errorMessage.textContent = '✓ 数据提取成功，请检查并确认数据准确性';
                        errorMessage.style.background = '#d4edda';
                        errorMessage.style.color = '#155724';
                        errorMessage.style.borderColor = '#c3e6cb';
                        errorMessage.classList.add('show');
                        
                        setTimeout(() => {
                            errorMessage.classList.remove('show');
                            errorMessage.style.background = '';
                            errorMessage.style.color = '';
                            errorMessage.style.borderColor = '';
                        }, 3000);
                    }
                    
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

            // 清除散光表单中由图片识别负责填充的字段，保留手工输入的 LT、WTW 和切口参数。
            ['Right', 'Left'].forEach(eye => {
                ['AL', 'FlatK', 'FlatAxis', 'SteepK', 'SteepAxis', 'ACD', 'MeasuredACD']
                    .forEach(field => {
                        document.getElementById('toric' + eye + field).value = '';
                    });
            });
            
            // 清除患者姓名和A常数
            document.getElementById('patientName').value = '';
            document.getElementById('iolModel').value = 'Personal Constant';
            document.getElementById('aConstant').value = '119.30'; // 恢复默认值
            document.getElementById('kIndex').value = '1.3375';
            document.getElementById('aConstant').readOnly = false;
            clearUlibConstants();
            ulibModelSearch.value = '';
            selectedUlibModelName = '';
            resetUlibHint();
            document.getElementById('aConstantHint').textContent =
                '默认值：119.30（可根据晶体类型调整）';
            document.getElementById('iolModelHint').textContent =
                '选择晶体型号可自动填充A常数';
            
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
            validateToricForm();
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

            // 公式常数仅回填，不自动切换公式；切换后无需重新识别。
            const constants = data.haigis_constants;
            if (constants && ['a0', 'a1', 'a2'].every((key) => Number.isFinite(Number(constants[key])))) {
                haigisA0.value = Number(constants.a0).toFixed(3);
                haigisA1.value = Number(constants.a1).toFixed(3);
                haigisA2.value = Number(constants.a2).toFixed(3);
            }
            if (data.hoffer_q_pacd !== null && data.hoffer_q_pacd !== undefined) {
                hofferQPacd.value = formatToTwoDecimals(data.hoffer_q_pacd);
            }

            // 同时把 AI 识别出的 K1/K2 及轴位填入散光表单，保持两种计算模式一致。
            const fillToricEye = (eye, eyeData) => {
                if (!eyeData) return;
                const prefix = eye === 'right' ? 'toricRight' : 'toricLeft';
                const values = {
                    FlatK: eyeData.K1,
                    FlatAxis: eyeData.K1Axis,
                    SteepK: eyeData.K2,
                    SteepAxis: eyeData.K2Axis,
                    AL: eyeData.AL,
                    ACD: eyeData.ACD,
                    MeasuredACD: eyeData.ACD
                };
                let hasValue = false;
                Object.entries(values).forEach(([field, value]) => {
                    if (value !== null && value !== undefined && value !== '') {
                        const input = document.getElementById(prefix + field);
                        if (input) input.value = value;
                        hasValue = true;
                    }
                });
                if (hasValue) {
                    const checkbox = document.getElementById(prefix + 'EyeEnabled');
                    checkbox.checked = true;
                    checkbox.dispatchEvent(new Event('change'));
                }
            };
            fillToricEye('right', data.right_eye);
            fillToricEye('left', data.left_eye);

            // 填充右眼数据
            if (data.right_eye && (data.right_eye.AL || data.right_eye.K1 || data.right_eye.K2 || (data.right_eye.ACD !== null && data.right_eye.ACD !== undefined))) {
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
            if (data.left_eye && (data.left_eye.AL || data.left_eye.K1 || data.left_eye.K2 || (data.left_eye.ACD !== null && data.left_eye.ACD !== undefined))) {
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
            validateToricForm();
            
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
                    iol_model: (selectedFormula === 'barrett'
                        ? document.getElementById('iolModel').value
                        : (selectedUlibModelName || undefined)),
                    k_index: parseFloat(document.getElementById('kIndex').value)
                };
                // 声明了晶体型号时交给后端查表，不再上报本地常数输入。
                const usesModelConstants = Boolean(activeUlibModelName());
                if (!usesModelConstants) {
                    formData.a_constant = roundToTwoDecimals(
                        document.getElementById('aConstant').value
                    );
                }

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

                const calculationModel = resolveCalculationModel();
                const haigisConstantsValue = calculationModel === 'haigis' && !usesModelConstants
                    ? readHaigisConstants() : null;
                const hofferQPacdValue = calculationModel === 'hoffer_q' && !usesModelConstants
                    ? parseFloat(hofferQPacd.value) : NaN;

                const payload = {
                    ...formData,
                    model: calculationModel
                };
                if (haigisConstantsValue) {
                    payload.haigis_constants = haigisConstantsValue;
                }
                if (Number.isFinite(hofferQPacdValue)) {
                    payload.hoffer_q_pacd = hofferQPacdValue;
                }

                const response = await fetch('/api/calculate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
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

        // Barrett Universal II Toric 独立表单
        const toricRightEyeEnabled = document.getElementById('toricRightEyeEnabled');
        const toricLeftEyeEnabled = document.getElementById('toricLeftEyeEnabled');
        const toricCalculateBtn = document.getElementById('toricCalculateBtn');
        const sphericalModeButton = document.getElementById('sphericalModeButton');
        const toricModeButton = document.getElementById('toricModeButton');
        const imageRecognitionSection = document.getElementById('imageRecognitionSection');
        const sphericalEyeSection = document.getElementById('sphericalEyeSection');
        const sphericalCalculateContainer = document.getElementById('sphericalCalculateContainer');
        const toricSection = document.getElementById('toricSection');
        const resultsSection = document.getElementById('resultsSection');
        const toricResultsSection = document.getElementById('toricResultsSection');
        const formulaSwitch = document.getElementById('formulaSwitch');
        const formulaButtons = Array.from(document.querySelectorAll('#formulaSwitch .formula-button'));
        const executionModeControls = document.getElementById('executionModeControls');
        const executionModeSwitch = document.getElementById('executionModeSwitch');
        const executionModeState = document.getElementById('executionModeState');
        const haigisConstants = document.getElementById('haigisConstants');
        const haigisA0 = document.getElementById('haigisA0');
        const haigisA1 = document.getElementById('haigisA1');
        const haigisA2 = document.getElementById('haigisA2');
        const hofferQPacdControls = document.getElementById('hofferQPacdControls');
        const hofferQPacd = document.getElementById('hofferQPacd');
        const executionModeHint = document.getElementById('executionModeHint');
        const formulaInputHint = document.getElementById('formulaInputHint');

        // Barrett 支持在线/本地，其他公式固定本地执行
        const EXECUTION_MODE_HINTS = {
            online: '在线调用 Barrett 官网，不保证稳定性',
            offline: '本地近似实现（Gaussian 聚散度 + 公开校准网格，非官方公式复刻），不保证准确性'
        };
        const LOCAL_FORMULA_HINT = '本地实现，基于公开发表公式；不保证准确性';
        const FORMULA_INPUT_HINTS = {
            barrett: 'Barrett 本地/在线均使用 ACD（可选）；本地还使用 LT/WTW（可选），缺失时会警告并降置信度。',
            srkt: 'SRK/T 由 A 常数和 K 自行推导 ACD；填写的 ACD、LT、WTW 会被忽略。',
            hoffer_q: 'Hoffer Q 可使用报告中的 pACD；留空则由 A 常数推导。填写的 ACD、LT、WTW 会被忽略。',
            haigis: 'Haigis 使用实测 ACD；a0/a1/a2 请照抄 IOL Master（不填则用 A 常数近似，可能差 1–3 D）；LT/WTW 会被忽略。'
        };

        // 型号选择器的 DOM 引用必须在使用前就绪：syncFormulaControls() 会在
        // 初始化阶段被调用，届时这些常量必须已经赋值。

        let selectedToricFormula = 'barrett';
        let toricCalculating = false;
        let ulibModels = [];
        let ulibModelsLoaded = false;
        let ulibLoading = false;

        let selectedFormula = 'barrett';
        let selectedExecutionMode = 'online';
        let currentCalculationMode = 'spherical';

        function updateFormulaButtons() {
            formulaButtons.forEach((button) => {
                const active = button.dataset.formula === selectedFormula;
                button.classList.toggle('active', active);
                button.setAttribute('aria-pressed', String(active));
            });
        }

        function updateExecutionToggle() {
            const online = selectedExecutionMode === 'online';
            executionModeSwitch.setAttribute('aria-checked', String(online));
            executionModeState.textContent = online ? '在线' : '本地';
        }

        function resolveExecutionMode() {
            if (selectedFormula !== 'barrett') {
                return 'offline';
            }
            return selectedExecutionMode === 'offline' ? 'offline' : 'online';
        }

        function resolveCalculationModel() {
            if (selectedFormula !== 'barrett') {
                return selectedFormula;
            }
            return selectedExecutionMode === 'offline' ? 'barrett_ii_offline' : 'barrett_ii';
        }


        // ---- ULIB 晶体选择器（非 Barrett 公式使用）----
        // 自绘下拉：输入关键词即时缩小候选，候选项只显示型号名。
        // 不用原生 datalist，因为它会再过滤一遍且各浏览器行为不一致。
        const barrettModelGroup = document.getElementById('barrettModelGroup');
        const ulibModelGroup = document.getElementById('ulibModelGroup');
        const ulibModelSearch = document.getElementById('ulibModelSearch');
        const ulibModelList = document.getElementById('ulibModelList');
        const ulibModelHint = document.getElementById('ulibModelHint');

        let selectedUlibModelName = '';

        async function loadUlibModels() {
            if (ulibModelsLoaded || ulibLoading) return;
            ulibLoading = true;
            try {
                const response = await fetch('/api/ulib-models');
                const result = await response.json();
                if (result.success && result.data && Array.isArray(result.data.models)) {
                    ulibModels = result.data.models;
                    ulibModelsLoaded = true;
                    ulibModelHint.textContent = '源自 ULIB Constants（2016-10-31）· '
                        + ulibModels.length + ' 款';
                } else {
                    throw new Error(result.message || '返回结构异常');
                }
            } catch (e) {
                ulibModelHint.textContent = 'ULIB 列表加载失败：' + e.message;
            } finally {
                ulibLoading = false;
            }
        }

        function filteredUlibModels(keyword) {
            // 空格分隔的多关键词按 AND 组合，任一关键词不命中就排除。
            const key = String(keyword || '').trim().toLowerCase();
            if (!key) return ulibModels;
            const terms = key.split(' ').filter(Boolean);
            return ulibModels.filter((model) => {
                const name = model.name.toLowerCase();
                return terms.every((term) => name.includes(term));
            });
        }

        function closeUlibList() {
            ulibModelList.hidden = true;
            ulibModelSearch.setAttribute('aria-expanded', 'false');
        }

        function renderUlibList() {
            const matched = filteredUlibModels(ulibModelSearch.value);
            ulibModelList.innerHTML = '';

            if (!ulibModelsLoaded) {
                const loading = document.createElement('li');
                loading.className = 'ulib-model-empty';
                loading.textContent = ulibLoading ? '正在加载…' : '列表尚未加载';
                ulibModelList.appendChild(loading);
            } else if (matched.length === 0) {
                const empty = document.createElement('li');
                empty.className = 'ulib-model-empty';
                empty.textContent = '没有匹配的晶体型号';
                ulibModelList.appendChild(empty);
            } else {
                const fragment = document.createDocumentFragment();
                matched.forEach((model) => {
                    const item = document.createElement('li');
                    item.className = 'ulib-model-item';
                    item.setAttribute('role', 'option');
                    item.dataset.modelName = model.name;
                    item.textContent = model.name;
                    fragment.appendChild(item);
                });
                ulibModelList.appendChild(fragment);
            }

            ulibModelList.hidden = false;
            ulibModelSearch.setAttribute('aria-expanded', 'true');
            ulibModelList.scrollTop = 0;
        }

        function findExactUlibModel(name) {
            const key = String(name || '').trim();
            if (!key) return null;
            const lower = key.toLowerCase();
            return ulibModels.find((model) => model.name.toLowerCase() === lower) || null;
        }

        function syncUlibSelection() {
            // 只有输入框内容恰好等于某个型号名时才认定为「选中」，
            // 半截关键词不会误填常数。
            const model = findExactUlibModel(ulibModelSearch.value);
            if (model === null) {
                if (selectedUlibModelName) {
                    selectedUlibModelName = '';
                    clearUlibConstants();
                    resetAConstantToDefault();
                    resetUlibHint();
                    syncFormulaControls();
                }
                return;
            }
            if (model.name === selectedUlibModelName) return;
            selectedUlibModelName = model.name;
            applyUlibModel(model);
        }

        function resetAConstantToDefault() {
            // 只在空着时补默认值，不覆盖用户已经填过的常数。
            aConstantInput.readOnly = false;
            if (!aConstantInput.value) aConstantInput.value = '119.30';
            document.getElementById('aConstantHint').textContent =
                '默认值：119.30（可根据晶体类型调整）';
        }

        function resetUlibHint() {
            document.getElementById('ulibModelHint').textContent = ulibModelsLoaded
                ? '源自 ULIB Constants（2016-10-31）· ' + ulibModels.length + ' 款'
                : '源自 ULIB Constants（2016-10-31）';
        }

        function pickUlibModel(name) {
            const model = findExactUlibModel(name);
            if (model === null) return;
            ulibModelSearch.value = model.name;
            selectedUlibModelName = model.name;
            applyUlibModel(model);
            closeUlibList();
            ulibModelSearch.blur();
        }

        ulibModelSearch.addEventListener('focus', function() {
            if (!ulibModelsLoaded && !ulibLoading) loadUlibModels();
            renderUlibList();
        });

        ulibModelSearch.addEventListener('input', function() {
            // 输入时先刷新候选，用户能立刻看到被关键词缩小后的结果。
            renderUlibList();
            syncUlibSelection();
        });

        ulibModelList.addEventListener('mousedown', function(event) {
            // 用 mousedown 抢在 input 的 blur 之前处理点击，避免列表先被关掉。
            const item = event.target.closest('.ulib-model-item');
            if (!item) return;
            event.preventDefault();
            pickUlibModel(item.dataset.modelName);
        });

        ulibModelSearch.addEventListener('keydown', function(event) {
            if (event.key === 'Escape') {
                closeUlibList();
                return;
            }
            const items = Array.from(ulibModelList.querySelectorAll('.ulib-model-item'));
            if (items.length === 0) return;
            const activeIndex = items.findIndex((el) => el.classList.contains('is-active'));
            if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
                event.preventDefault();
                const step = event.key === 'ArrowDown' ? 1 : -1;
                let next = activeIndex + step;
                if (next < 0) next = items.length - 1;
                if (next >= items.length) next = 0;
                items.forEach((el) => el.classList.remove('is-active'));
                items[next].classList.add('is-active');
                items[next].scrollIntoView({ block: 'nearest' });
                return;
            }
            if (event.key === 'Enter' && activeIndex >= 0) {
                event.preventDefault();
                pickUlibModel(items[activeIndex].dataset.modelName);
            }
        });

        ulibModelSearch.addEventListener('blur', function() {
            // 焦点离开后若没选中任何型号，把半截关键词还原成空，
            // 避免看起来像已选但实际常数没生效。
            syncUlibSelection();
            if (!selectedUlibModelName) ulibModelSearch.value = '';
            closeUlibList();
        });

        document.addEventListener('click', function(event) {
            if (!ulibModelGroup.contains(event.target)) closeUlibList();
        });

        function ulibConstantsSummary(model) {
            // 只把型号常数显示成说明文字，不写进输入框；真实取值由后端查表。
            const parts = [];
            if (model.a_constant !== null && model.a_constant !== undefined) {
                parts.push('A ' + Number(model.a_constant).toFixed(2));
            }
            if (model.haigis && model.haigis.length === 3) {
                parts.push('Haigis ' + model.haigis
                    .map(value => Number(value).toFixed(3)).join(' / '));
            }
            if (model.pacd !== null && model.pacd !== undefined) {
                parts.push('pACD ' + Number(model.pacd).toFixed(2));
            }
            return parts;
        }

        function applyUlibModel(model) {
            // 声明型号后常数由 calculate 内部查表：输入框锁定但保留用户
            // 原来填的值，只显示将采用的常数，避免把查表值伪装成输入。
            const parts = ulibConstantsSummary(model);
            if (parts.length === 0) {
                setConstantInputsLocked(false);
                document.getElementById('ulibModelHint').textContent =
                    '该型号缺少可用常数，请手动填写';
                return;
            }
            lockUlibConstants();
            let hint = '按型号查表：' + parts.join(' · ');
            if (model.preliminary) hint += '（样本量偏小，仅供参考）';
            document.getElementById('ulibModelHint').textContent = hint;
            document.getElementById('aConstantHint').textContent =
                '由所选型号决定，输入框值不参与计算';
        }

        function activeUlibModelName() {
            // 只有本地公式走 ULIB 查表；Barrett 用官网型号和自己的常数。
            if (currentCalculationMode === 'toric') {
                return selectedToricFormula === 'haigis-toric'
                    ? selectedUlibModelName : '';
            }
            return selectedFormula !== 'barrett' ? selectedUlibModelName : '';
        }

        function setConstantInputsLocked(locked) {
            // 只切可编辑状态，不动输入值：用户自己填的常数切回来还在。
            Object.entries(FORMULA_CONSTANT_FIELDS).forEach(([id, placeholder]) => {
                const input = document.getElementById(id);
                if (!input) return;
                input.disabled = locked;
                input.placeholder = locked ? '由所选型号决定' : placeholder;
            });
            aConstantInput.readOnly = locked;
        }

        function refreshConstantLock() {
            // 切公式/切模式后同步锁定状态：声明了型号就锁输入框，
            // 让常数由后端按型号查表；否则恢复可编辑。
            if (activeUlibModelName()) {
                setConstantInputsLocked(true);
                const model = findExactUlibModel(selectedUlibModelName);
                if (model) applyUlibModel(model);
                return;
            }
            setConstantInputsLocked(false);
            // 解锁后输入框仍是用户原值；只有空值时补默认，免得 Barrett
            // 分支带着空值提交。
            if (!aConstantInput.value) resetAConstantToDefault();
            resetUlibHint();
        }

        function syncModelSelectors() {
            // 晶体列表跟着当前生效的公式走：
            //   非散光模式看 selectedFormula；散光模式看 selectedToricFormula。
            // Barrett 系列（含 Barrett Toric）用 Barrett 官网型号列表，
            // 只有 Haigis 与 Haigis-T 用 ULIB 列表。
            const isToric = currentCalculationMode === 'toric';
            const activeFormula = isToric ? selectedToricFormula : selectedFormula;
            const useBarrettList = activeFormula === 'barrett';
            barrettModelGroup.hidden = !useBarrettList;
            ulibModelGroup.hidden = useBarrettList;
            if (!useBarrettList) loadUlibModels();
            refreshConstantLock();
        }

        function syncFormulaControls() {
            const isBarrett = selectedFormula === 'barrett';
            executionModeControls.hidden = !isBarrett;
            executionModeHint.textContent = isBarrett
                ? EXECUTION_MODE_HINTS[resolveExecutionMode()]
                : LOCAL_FORMULA_HINT;
            formulaInputHint.textContent = FORMULA_INPUT_HINTS[selectedFormula] || '';
            haigisConstants.hidden = selectedFormula !== 'haigis';
            hofferQPacdControls.hidden = selectedFormula !== 'hoffer_q';
            syncModelSelectors();
        }

        function hasAnyEyeData() {
            // 检查是否已有任何一眼的核心数据，用于切换公式时给出"参数已保留"提示。
            return ['right', 'left'].some((eye) => {
                const enabled = document.getElementById(eye + 'EyeEnabled');
                const al = document.getElementById(eye + 'AL');
                const k1 = document.getElementById(eye + 'K1');
                const k2 = document.getElementById(eye + 'K2');
                return enabled && enabled.checked && al.value && k1.value && k2.value;
            });
        }

        function selectFormula(name) {
            // 只切换公式与执行方式控件的可见性/状态，绝不清空任何输入；
            // 双眼参数、A 常数、K-index、Haigis 常数、患者信息全部保留，
            // 执行模式也保持用户上一次的选择，避免切回 Barrett 时被强制 online。
            const changed = selectedFormula !== name;
            selectedFormula = name;
            updateFormulaButtons();
            updateExecutionToggle();
            syncFormulaControls();
            validateForm();
            if (changed && hasAnyEyeData()) {
                const base = FORMULA_INPUT_HINTS[name] || '';
                formulaInputHint.textContent = '✓ 已保留之前填写/识别的参数，可直接计算。' + base;
            }
        }

        function selectExecutionMode(mode) {
            selectedExecutionMode = mode === 'offline' ? 'offline' : 'online';
            updateExecutionToggle();
            syncFormulaControls();
        }

        function readHaigisConstants() {
            const a0 = parseFloat(haigisA0.value);
            const a1 = parseFloat(haigisA1.value);
            const a2 = parseFloat(haigisA2.value);
            if (![a0, a1, a2].every(Number.isFinite)) return null;
            return {a0: a0, a1: a1, a2: a2};
        }

        function setCalculationMode(mode) {
            const isToric = mode === 'toric';
            currentCalculationMode = isToric ? 'toric' : 'spherical';
            sphericalModeButton.classList.toggle('active', !isToric);
            sphericalModeButton.setAttribute('aria-pressed', String(!isToric));
            toricModeButton.classList.toggle('active', isToric);
            toricModeButton.setAttribute('aria-pressed', String(isToric));
            imageRecognitionSection.hidden = false;
            sphericalEyeSection.hidden = isToric;
            sphericalCalculateContainer.hidden = isToric;
            toricSection.hidden = !isToric;
            resultsSection.hidden = isToric;
            toricResultsSection.hidden = !isToric;
            formulaSwitch.hidden = isToric;
            document.getElementById('toricFormulaSwitch').hidden = !isToric;
            document.getElementById('toricFormulaHint').hidden = !isToric;
            executionModeHint.hidden = isToric;
            formulaInputHint.hidden = isToric;
            haigisConstants.hidden = isToric;
            hofferQPacdControls.hidden = isToric;
            syncModelSelectors();
            if (isToric) {
                executionModeControls.hidden = true;
            }

            if (isToric) {
                syncToricFormulaControls();
            } else {
                document.getElementById('aConstantGroup').hidden = false;
                aConstantInput.required = true;
                document.getElementById('haigisConstantsNote').textContent = '照抄 IOL Master 的 a0/a1/a2；不填则用 A 常数近似';
                syncFormulaControls();
                validateForm();
            }
        }

        sphericalModeButton.addEventListener('click', () => setCalculationMode('spherical'));
        toricModeButton.addEventListener('click', () => setCalculationMode('toric'));
        formulaButtons.forEach((button) => {
            button.addEventListener('click', () => selectFormula(button.dataset.formula));
        });
        executionModeSwitch.addEventListener('click', () => {
            selectExecutionMode(selectedExecutionMode === 'online' ? 'offline' : 'online');
        });
        updateFormulaButtons();
        updateExecutionToggle();

        function toricPrefix(eye) {
            return eye === 'right' ? 'toricRight' : 'toricLeft';
        }

        function syncToricFormulaControls() {
            const isHaigis = selectedToricFormula === 'haigis-toric';
            document.querySelectorAll('[data-toric-formula]').forEach(button => {
                const active = button.dataset.toricFormula === selectedToricFormula;
                button.classList.toggle('active', active);
                button.setAttribute('aria-pressed', String(active));
            });
            document.querySelectorAll('[data-toric-only]').forEach(group => {
                group.hidden = group.dataset.toricOnly !== selectedToricFormula;
            });
            document.getElementById('toricSectionTitle').textContent = isHaigis
                ? 'Haigis-T 散光晶体' : 'Barrett Universal II 散光晶体';
            document.getElementById('toricFormulaHint').textContent = isHaigis
                ? '本地公开框架近轴实现；完整商用算法未核实，结果为低置信度。'
                : '在线调用 Barrett Toric 官网，不保证稳定性。';
            document.getElementById('toricInputHint').textContent = isHaigis
                ? '必填：晶体型号（或完整 a0/a1/a2）、AL、前表面 K1/K2 及正交轴位、术前实测 ACD。标有 * 的参数必填；LT、WTW、A 常数不参与计算。切口 SIA 表示沿切口方向的扁平化量。'
                : '使用上方患者、晶体型号、A 常数和 K-index 设置；请至少启用一眼。标有 * 的参数必填。';
            haigisConstants.hidden = !isHaigis;
            document.getElementById('haigisConstantsNote').textContent = isHaigis
                ? '选择晶体型号后由该型号常数计算；未选型号时须完整填写 a0/a1/a2。'
                : '照抄 IOL Master 的 a0/a1/a2；不填则用 A 常数近似';
            document.getElementById('aConstantGroup').hidden = isHaigis;
            aConstantInput.required = !isHaigis;
            ['right', 'left'].forEach(syncToricPosteriorControls);
            syncModelSelectors();
            validateToricForm();
        }

        function syncToricPosteriorControls(eye) {
            const prefix = toricPrefix(eye);
            const mode = document.getElementById(prefix + 'PosteriorMode').value;
            document.querySelectorAll('#' + prefix + 'EyeParams [data-posterior-mode]').forEach(group => {
                group.hidden = group.dataset.posteriorMode !== mode;
            });
            const hints = {
                none: 'PCA 未计入：WTR 可能过矫，ATR 可能欠矫。',
                measured: '填写角膜平面的后表面光学散光与光学强子午线。',
                total: '总散光替换前表面与 PCA 矢量；球镜仍使用前表面平均 K。',
                estimated: 'UNVERIFIED-PENDING-PRIMARY：固定 0.30 D @0° ATR 代理，并非已核实的 Haigis-T 个体化系数。'
            };
            document.getElementById(prefix + 'PosteriorHint').textContent = hints[mode];
        }

        function readCylinderPowers(eye) {
            const raw = document.getElementById(toricPrefix(eye) + 'CylinderPowers').value.trim();
            if (!raw) return undefined;
            const tokens = raw.split(/[,，;；]/).map(token => token.trim());
            if (tokens.some(token => !token || !Number.isFinite(Number(token)) || Number(token) < 0)) {
                throw new Error('可供柱镜档位须为非负数，请用逗号分隔，勿留空档位。');
            }
            return tokens.map(Number);
        }

        function toricEyeValidationError(eye) {
            const prefix = toricPrefix(eye);
            const isHaigis = selectedToricFormula === 'haigis-toric';
            const required = ['AL', 'FlatK', 'FlatAxis', 'SteepK', 'SteepAxis'];
            if (isHaigis) {
                required.push('MeasuredACD');
                const mode = document.getElementById(prefix + 'PosteriorMode').value;
                if (mode === 'measured') required.push('PosteriorCylinder', 'PosteriorAxis');
                if (mode === 'total') required.push('TotalCylinder', 'TotalAxis');
                if (Number(document.getElementById(prefix + 'IolCylinder').value) > 0) required.push('IolAxis');
                if (Number(document.getElementById(prefix + 'SIA').value) > 0) required.push('HaigisIncision');
            } else {
                required.push('LT', 'WTW');
            }
            const inputs = Array.from(document.querySelectorAll('#' + prefix + 'EyeParams input')).filter(input => !input.closest('[hidden]'));
            inputs.forEach(input => input.required = required.includes(input.id.slice(prefix.length)));
            for (const input of inputs) {
                if (!input.checkValidity()) {
                    const label = document.querySelector('label[for="' + input.id + '"]');
                    return '请填写或检查' + label.textContent + '。';
                }
            }
            const value = suffix => Number(document.getElementById(prefix + suffix).value);
            if (isHaigis) {
                if (value('SteepK') < value('FlatK')) return 'K2 必须不小于 K1。';
                const difference = ((value('SteepAxis') - value('FlatAxis')) % 180 + 180) % 180;
                if (Math.abs(difference - 90) > 0.000001) return 'K1 与 K2 轴位必须正交（相差 90°）。';
                try { readCylinderPowers(eye); } catch (error) { return error.message; }
            }
            return '';
        }

        function validateToricForm() {
            const enabled = ['right', 'left'].filter(eye => document.getElementById(toricPrefix(eye) + 'EyeEnabled').checked);
            let error = enabled.length ? '' : '请至少启用一只眼睛并填写参数。';
            if (selectedToricFormula === 'haigis-toric') {
                // 已声明型号时三常数由后端查表，不再要求手工填写。
                const constantsValid = Boolean(selectedUlibModelName) ||
                    [haigisA0, haigisA1, haigisA2].every(input => input.value !== '' && input.checkValidity());
                if (!constantsValid) error = '请选择晶体型号，或完整填写有效的 Haigis a0、a1、a2 常数。';
            } else if (!aConstantInput.value || !aConstantInput.checkValidity()) {
                error = '请填写有效的 A 常数。';
            }
            // 任一启用眼无效都禁止提交，避免把另一只眼的缺失值送入 API。
            for (const eye of enabled) {
                const eyeError = toricEyeValidationError(eye);
                if (!error && eyeError) error = (eye === 'right' ? '右眼：' : '左眼：') + eyeError;
            }
            document.getElementById('toricValidationHint').textContent = error;
            toricCalculateBtn.disabled = toricCalculating || Boolean(error);
            return !error;
        }

        function setToricEyeState(eye, enabled) {
            const prefix = toricPrefix(eye);
            document.getElementById(prefix + 'EyeParams').classList.toggle('show', enabled);
            document.getElementById(prefix + 'EyeSection').classList.toggle('active', enabled);
            validateToricForm();
        }

        document.querySelectorAll('[data-toric-formula]').forEach(button => {
            button.addEventListener('click', () => {
                selectedToricFormula = button.dataset.toricFormula;
                toricResultsSection.classList.remove('show');
                syncToricFormulaControls();
            });
        });
        toricRightEyeEnabled.addEventListener('change', function() {
            setToricEyeState('right', this.checked);
        });
        toricLeftEyeEnabled.addEventListener('change', function() {
            setToricEyeState('left', this.checked);
        });
        ['right', 'left'].forEach(eye => {
            document.getElementById(toricPrefix(eye) + 'PosteriorMode').addEventListener('change', () => {
                syncToricPosteriorControls(eye);
                validateToricForm();
            });
        });
        document.querySelectorAll('#toricSection input, #toricSection select, #haigisConstants input, #aConstant').forEach(input => {
            input.addEventListener('input', validateToricForm);
            input.addEventListener('change', validateToricForm);
        });
        setCalculationMode('spherical');

        function readToricEyeData(eye) {
            const prefix = toricPrefix(eye);
            const number = suffix => {
                const value = document.getElementById(prefix + suffix).value;
                return value === '' ? undefined : Number(value);
            };
            const data = {
                K1: number('FlatK'), K1Axis: number('FlatAxis'),
                K2: number('SteepK'), K2Axis: number('SteepAxis'),
                AL: number('AL'),
                incision_sia: number('SIA') ?? 0,
                incision_location: number('Incision')
            };
            if (selectedToricFormula === 'haigis-toric') {
                data.incision_location = number('HaigisIncision');
                data.ACD = roundToTwoDecimals(number('MeasuredACD'));
                data.Refraction = number('Refraction') ?? 0;
                data.iol_cylinder = number('IolCylinder') ?? 0;
                data.iol_axis = number('IolAxis');
                data.iol_spherical_equivalent = number('IolSE');
                data.cylinder_powers = readCylinderPowers(eye);
                data.posterior_mode = document.getElementById(prefix + 'PosteriorMode').value;
                if (data.posterior_mode === 'measured') {
                    data.posterior_cylinder = number('PosteriorCylinder');
                    data.posterior_axis = number('PosteriorAxis');
                } else if (data.posterior_mode === 'total') {
                    data.total_cylinder = number('TotalCylinder');
                    data.total_axis = number('TotalAxis');
                    data.total_source = document.getElementById(prefix + 'TotalSource').value;
                }
            } else {
                data.ACD = number('ACD');
                data.target_refraction = number('Refraction');
                data.lens_thickness = number('LT');
                data.WTW = number('WTW');
            }
            return data;
        }

        function escapeHtml(value) {
            return String(value ?? '').replace(/[&<>"']/g, char => ({
                '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
            }[char]));
        }

        toricCalculateBtn.addEventListener('click', async function() {
            if (toricCalculating || !validateToricForm()) return;
            const requestFormula = selectedToricFormula;
            toricCalculating = true;
            const errorMessage = document.getElementById('errorMessage');
            const loading = document.getElementById('loading');
            const toricResultsSection = document.getElementById('toricResultsSection');
            errorMessage.classList.remove('show');
            toricResultsSection.classList.remove('show');
            loading.classList.add('show');
            toricCalculateBtn.disabled = true;

            try {
                const formData = {
                    patient_name: document.getElementById('patientName').value || null,
                    a_constant: roundToTwoDecimals(document.getElementById('aConstant').value),
                    iol_model: (selectedToricFormula === 'haigis-toric'
                        ? (selectedUlibModelName || undefined)
                        : document.getElementById('iolModel').value),
                    k_index: parseFloat(document.getElementById('kIndex').value)
                };
                if (requestFormula === 'haigis-toric') {
                    formData.model = 'haigis-toric';
                    // 声明型号后常数由后端查表，不再提交本地输入值。
                    if (!selectedUlibModelName) {
                        formData.haigis_constants = readHaigisConstants();
                    }
                    delete formData.a_constant;
                } else {
                    formData.cylinder_mode = document.getElementById('toricCylinderMode').value;
                }
                if (toricRightEyeEnabled.checked) formData.right_eye = readToricEyeData('right');
                if (toricLeftEyeEnabled.checked) formData.left_eye = readToricEyeData('left');

                const options = {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                };
                const response = requestFormula === 'haigis-toric'
                    ? await fetch('/api/calculate', options)
                    : await fetch('/api/calculate-toric', options);
                const result = await response.json();
                if (response.ok && result.success) {
                    // 等待时若切换了公式，不展示旧公式的返回结果。
                    if (selectedToricFormula === requestFormula) displayToricResults(result.data, requestFormula);
                } else {
                    throw new Error(result.message || '散光计算失败');
                }
            } catch (error) {
                errorMessage.textContent = '错误：' + error.message;
                errorMessage.classList.add('show');
            } finally {
                loading.classList.remove('show');
                toricCalculating = false;
                validateToricForm();
            }
        });

        function displayToricResults(data, formula) {
            const resultsContent = document.getElementById('toricResultsContent');
            resultsContent.innerHTML = '';
            if (formula === 'haigis-toric') resultsContent.appendChild(createFormulaSummary(data));
            let hasResult = false;
            [['right_eye', '右眼 (OD)'], ['left_eye', '左眼 (OS)']].forEach(([key, title]) => {
                if (data[key]) {
                    resultsContent.appendChild(formula === 'haigis-toric'
                        ? createHaigisToricResultCard(title, data[key])
                        : createToricResultCard(title, data[key], key));
                    hasResult = true;
                }
            });
            if (!hasResult) {
                resultsContent.innerHTML = '<p style="text-align: center; color: #666; padding: 20px;">暂无散光计算结果</p>';
            }
            document.getElementById('toricResultsSection').classList.add('show');
        }

        function createHaigisToricResultCard(title, eyeData) {
            const card = document.createElement('div');
            card.className = 'result-card';
            const format = (value, unit = ' D') => value === null || value === undefined
                ? '—' : escapeHtml(Number(value).toFixed(2)) + unit;
            const axis = value => format(value, '°');
            const residual = eyeData.residual_astigmatism || {};
            let html = '<h4>' + escapeHtml(title) + ' · Haigis-T</h4>';
            html += '<dl class="toric-result-details">';
            html += '<dt>拟植入方案的预期残余散光（角膜平面）</dt><dd>' + format(residual.cylinder) + '；光学强子午线 ' + axis(residual.axis) + '；等效负柱镜轴位 ' + axis(residual.minus_cylinder_axis) + '</dd>';
            html += '<dt>本次残余预测使用的植入参数</dt><dd>IOL SE ' + format(eyeData.iol_spherical_equivalent) + '；柱镜 ' + format(eyeData.iol_cylinder) + '；植入轴位 ' + axis(eyeData.iol_axis) + '</dd>';
            html += '<dt>IOL 柱镜在角膜平面的等效矫正</dt><dd>' + format(eyeData.corneal_correction) + '（ELP 相关乘数 ' + format(eyeData.corneal_factor, '') + '）</dd>';
            html += '<dt>推荐 IOL 柱镜与轴位</dt><dd>连续解 ' + format(eyeData.recommended_iol_cylinder_exact) + '；可供档位 ' + (eyeData.recommended_iol_cylinder == null ? '未提供档位，不作离散推荐' : format(eyeData.recommended_iol_cylinder)) + '；建议轴位 ' + axis(eyeData.recommended_axis) + '</dd></dl>';
            const toricOptions = eyeData.toric_options || [];
            if (toricOptions.length) {
                html += '<div class="toric-table-scroll"><table class="result-table"><caption>可供档位按各自最佳轴位比较（角膜平面残余）</caption><thead><tr><th>IOL 柱镜</th><th>建议轴位</th><th>等效矫正</th><th>残余量值</th></tr></thead><tbody>';
                toricOptions.forEach(option => {
                    html += '<tr class="' + (option.recommended ? 'recommended' : '') + '"><td>' + format(option.iol_cylinder) + (option.recommended ? '（推荐）' : '') + '</td><td>' + axis(option.axis) + '</td><td>' + format(option.corneal_correction) + '</td><td>' + format(option.residual_astigmatism.cylinder) + '</td></tr>';
                });
                html += '</tbody></table></div>';
            }
            html += '<p class="param-hint toric-form-note">植入轴位表示 IOL 光学弱子午线的对齐方向。上方残余对应拟植入方案；档位表按最佳轴位比较。零散光无定义轴位时显示 —。</p>';
            html += '<div class="toric-table-scroll"><table class="result-table"><caption>Haigis 球镜 SE 候选（非完整术后球柱镜处方）</caption><thead><tr><th>IOL 球镜等效 SE</th><th>球镜预期屈光度</th></tr></thead><tbody>';
            (eyeData.iol_options || []).forEach(option => {
                html += '<tr class="' + (option.recommended ? 'recommended' : '') + '"><td>' + escapeHtml(option.iol_power) + ' D</td><td>' + escapeHtml(option.refraction) + ' D</td></tr>';
            });
            html += '</tbody></table></div>';
            card.innerHTML = html;
            return card;
        }

        function createToricResultCard(title, eyeData, eyeKey) {
            const card = document.createElement('div');
            card.className = 'result-card';
            const options = Array.isArray(eyeData.iol_options) ? eyeData.iol_options : [];
            let html = '<h4>' + escapeHtml(title) + '</h4>';
            if (options.length > 0) {
                html += '<table class="result-table"><thead><tr><th>球镜 IOL</th><th>散光型号</th><th>轴位</th><th>预期屈光度</th></tr></thead><tbody>';
                options.forEach((option, index) => {
                    const recommended = option.recommended || index === 0;
                    html += '<tr class="' + (recommended ? 'recommended' : '') + '">';
                    html += '<td>' + escapeHtml(option.iol_power) + (recommended ? '（推荐）' : '') + '</td>';
                    html += '<td>' + escapeHtml(option.toric_power) + '</td>';
                    html += '<td>' + escapeHtml(option.axis) + '°</td>';
                    html += '<td>' + escapeHtml(option.refraction) + '</td></tr>';
                });
                html += '</tbody></table>';
            } else {
                html += '<p class="param-hint">官方页面未返回可列出的晶体表格，请核对输入和上游页面状态。</p>';
            }
            card.innerHTML = html;
            const axisImage = eyeData.axis_image || {};
            const axisResult = document.createElement('div');
            axisResult.className = 'axis-result';
            axisResult.innerHTML = createAxisImageHtml(axisImage, eyeKey);
            card.appendChild(axisResult);
            return card;
        }

        function createAxisImageHtml(axisImage, eyeKey) {
            const toric = axisImage.toric_axis;
            const source = axisImage.source_url || 'https://calc.apacrs.org/toric_calculator20/Resources/Eye%20Background%20360.jpg';
            const fallback = axisImage.fallback_url || '';
            const line = (axis, className) => axis === null || axis === undefined || axis === '' ? '' :
                '<span class="axis-line ' + className + '" style="transform: rotate(' + Number(axis) + 'deg);"></span>';
            return '<h5>原版 Barrett Toric 轴位图</h5>' +
                '<div class="axis-layout"><div class="axis-figure">' +
                '<img src="' + escapeHtml(source) + '" data-fallback="' + escapeHtml(fallback) + '" alt="Barrett Toric 轴位图" loading="lazy" onerror="if(this.dataset.fallback){this.onerror=null;this.src=this.dataset.fallback;}else{this.style.display=&quot;none&quot;;}">' +
                line(toric, 'toric') +
                '</div><div class="axis-legend">' +
                '<div class="axis-legend-row"><span>IOL 建议轴位</span><strong>' + escapeHtml(toric) + '°</strong></div>' +
                '<div class="param-hint">轴位图背景来自 Barrett Toric 官方计算器；绿色细线表示建议植入轴位。</div>' +
                '</div></div>';
        }

        function formatUsedInputs(used) {
            if (!used) return '';
            const parts = [];
            const labels = [['AL', 'AL'], ['K', 'K'], ['ACD', 'ACD'], ['LenThickness', 'LT'], ['WTW', 'WTW'], ['Refraction', '目标']];
            labels.forEach((item) => {
                const key = item[0];
                const label = item[1];
                if (used[key] === null || used[key] === undefined) return;
                let value = used[key];
                if (key === 'ACD' && used.ACD_defaulted) value += '(默认)';
                parts.push(label + '=' + value);
            });
            if (used.a_constant !== null && used.a_constant !== undefined) parts.push('A=' + used.a_constant);
            if (used.a0 !== null && used.a0 !== undefined) parts.push('a0=' + used.a0);
            if (used.a1 !== null && used.a1 !== undefined) parts.push('a1=' + used.a1);
            if (used.a2 !== null && used.a2 !== undefined) parts.push('a2=' + used.a2);
            return parts.join(', ');
        }

        function createFormulaSummary(data) {
            const formulaLabel = data && data.formula_label ? data.formula_label : 'Barrett Universal II';
            const modeLabel = data && data.mode === 'online' ? '在线' : '本地';
            const lines = ['公式：' + formulaLabel + '（' + modeLabel + '）'];
            const source = data && data.constants_source;
            if (source && source.source === 'ulib') {
                lines.push('常数来源：ULIB ' + (source.ulib_name || '')
                    + (source.ignored_request && source.ignored_request.length
                        ? '（已忽略请求中的 ' + source.ignored_request.join('、') + '）'
                        : ''));
            }
            [['右眼', 'right_eye'], ['左眼', 'left_eye']].forEach((item) => {
                const label = item[0];
                const eye = data && data[item[1]];
                if (!eye) return;
                const confidence = eye.confidence === 'LOW_CONFIDENCE' ? '低置信度' : (eye.confidence || '未知');
                lines.push(label + '：置信度 ' + confidence);
                if (eye.constants) lines.push('  常数：' + eye.constants);
                if (eye.elp !== null && eye.elp !== undefined) lines.push('  ELP：' + eye.elp + ' mm');
                const used = formatUsedInputs(eye.used_inputs);
                if (used) lines.push('  使用输入：' + used);
                if (eye.ignored_inputs && eye.ignored_inputs.length) lines.push('  未使用：' + eye.ignored_inputs.join('、'));
                if (eye.warnings && eye.warnings.length) lines.push('  警告：' + eye.warnings.join('；'));
            });
            const summary = document.createElement('div');
            summary.className = 'formula-summary';
            summary.textContent = lines.join(String.fromCharCode(10));
            return summary;
        }

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
                resultsContent.insertBefore(createFormulaSummary(data), resultsContent.firstChild);
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

            // 统一按晶体度数从低到高显示，避免不同公式返回顺序不一致
            const sortedOptions = (eyeData.iol_options || []).slice().sort(
                (a, b) => parseFloat(a.iol_power) - parseFloat(b.iol_power)
            );

            // 根据目标屈光度找到最接近的晶体度数
            let closestOption = null;
            let minDiff = Infinity;
            
            // 首先重置所有选项的推荐状态
            sortedOptions.forEach(option => {
                option.recommended = false;
            });
            
            // 找到最接近目标屈光度的选项
            sortedOptions.forEach(option => {
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

            sortedOptions.forEach(option => {
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
