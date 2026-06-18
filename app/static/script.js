/**
 * 糖尿病风险筛查工具 - 前端交互脚本
 * ========================================
 * 免责声明弹窗 / 标签页切换 / 随机填充 / BMI 计算 / 结果渲染
 * 与微信小程序端功能同步
 */

(function () {
    "use strict";

    // ================================================================
    // 风险等级配置 (对齐 miniapp/components/result-card/result-card.js)
    // ================================================================
    var LEVEL_CONFIG = {
        1: { bg: "#EDF5F1", icon: "🟢" },
        2: { bg: "#FDF8EE", icon: "🟡" },
        3: { bg: "#FDF3ED", icon: "🟠" },
        4: { bg: "#FDF0EF", icon: "🔴" },
        5: { bg: "#FEF0EF", icon: "⛔" },
    };

    // ================================================================
    // 随机填充示例数据 (对齐 miniapp/pages/index/index.js)
    // ================================================================
    var PROFILES = [
        {
            label: "低风险示例",
            age: "28", genderVal: "男性", genderAdvVal: "男性",
            hba1c: "5.1", fastingGlucose: "4.8",
            height: "160", weight: "52",
            homaIr: "1.2", egfr: "105", urdact: "8",
            bpSys: "108", bpDia: "68",
            triglyc: "85", ggt: "18", uricAcid: "4.2", alt: "16", vitD3: "65",
        },
        {
            label: "中风险示例",
            age: "52", genderVal: "男性", genderAdvVal: "男性",
            hba1c: "5.9", fastingGlucose: "6.2",
            height: "172", weight: "78",
            homaIr: "2.8", egfr: "82", urdact: "25",
            bpSys: "138", bpDia: "85",
            triglyc: "180", ggt: "42", uricAcid: "6.5", alt: "35", vitD3: "38",
        },
        {
            label: "高风险示例",
            age: "65", genderVal: "男性", genderAdvVal: "男性",
            hba1c: "7.2", fastingGlucose: "8.5",
            height: "168", weight: "92",
            homaIr: "4.5", egfr: "58", urdact: "85",
            bpSys: "155", bpDia: "95",
            triglyc: "260", ggt: "78", uricAcid: "8.2", alt: "52", vitD3: "22",
        },
    ];

    // ================================================================
    // 免责声明弹窗
    // ================================================================
    var countdownTimer = null;
    var agreed = false;
    var countdownDone = false;
    var countdownSec = 10;

    /** 更新按钮状态 — 两个独立条件都满足才启用 */
    function updateProceedState() {
        var btn = document.getElementById("disclaimer-btn");
        if (!btn) return;
        if (agreed && countdownDone) {
            btn.textContent = "进入测试";
            btn.classList.add("disclaimer-btn-active");
            btn.disabled = false;
        } else {
            btn.textContent = "请阅读并勾选同意";
            btn.classList.remove("disclaimer-btn-active");
            btn.disabled = true;
        }
    }

    /** 启动倒计时 */
    function startCountdown() {
        var hint = document.getElementById("countdown-hint");
        countdownTimer = setInterval(function () {
            countdownSec--;
            if (hint) hint.textContent = "阅读倒计时 " + countdownSec + " 秒";
            if (countdownSec <= 0) {
                clearInterval(countdownTimer);
                countdownTimer = null;
                countdownDone = true;
                if (hint) hint.style.display = "none";
                updateProceedState();
            }
        }, 1000);
    }

    /** 勾选/取消免责声明 */
    function toggleAgree() {
        var checkbox = document.getElementById("check-box");
        if (countdownDone && agreed) return; // 已可进入，不允许取消
        agreed = !agreed;
        if (checkbox) {
            if (agreed) {
                checkbox.classList.add("check-box-on");
                checkbox.innerHTML = '<span class="check-mark">✓</span>';
            } else {
                checkbox.classList.remove("check-box-on");
                checkbox.innerHTML = "";
            }
        }
        updateProceedState();
    }

    /** 关闭弹窗 */
    function dismissDisclaimer() {
        if (!(agreed && countdownDone)) return;
        if (countdownTimer) {
            clearInterval(countdownTimer);
            countdownTimer = null;
        }
        var overlay = document.getElementById("disclaimer-overlay");
        if (overlay) {
            overlay.style.display = "none";
        }
    }

    // 导出免责声明处理函数到全局作用域
    window._toggleAgree = toggleAgree;
    window._dismissDisclaimer = dismissDisclaimer;

    // ================================================================
    // DOMContentLoaded
    // ================================================================
    document.addEventListener("DOMContentLoaded", function () {
        // 启动倒计时
        startCountdown();

        // ================================================================
        // 标签页切换
        // ================================================================
        var tabBtns = document.querySelectorAll(".tab-btn");
        var tabContents = document.querySelectorAll(".tab-content");

        tabBtns.forEach(function (btn) {
            btn.addEventListener("click", function () {
                var targetId = this.getAttribute("data-tab");
                tabBtns.forEach(function (b) { b.classList.remove("active"); });
                tabContents.forEach(function (c) { c.classList.remove("active"); });
                this.classList.add("active");
                var target = document.getElementById(targetId);
                if (target) {
                    target.classList.add("active");
                    target.scrollIntoView({ behavior: "smooth", block: "start" });
                }
            });
        });

        // ================================================================
        // BMI 实时计算
        // ================================================================
        function calcBMI(suffix) {
            var hEl = document.getElementById((suffix === "basic" ? "basic" : "adv") + "-height");
            var wEl = document.getElementById((suffix === "basic" ? "basic" : "adv") + "-weight");
            var bmiDisplay = document.getElementById(suffix + "-bmi-display");
            var bmiHidden = document.getElementById(suffix + "-bmi-hidden");
            if (!hEl || !wEl || !bmiDisplay) return;

            var h = parseFloat(hEl.value);
            var w = parseFloat(wEl.value);
            if (h > 0 && w > 0) {
                var bmi = w / Math.pow(h / 100, 2);
                bmiDisplay.textContent = "BMI: " + bmi.toFixed(1) + " kg/m²";
                bmiDisplay.style.color = "";
                if (bmiHidden) bmiHidden.value = bmi.toFixed(1);
            } else {
                bmiDisplay.textContent = "BMI: -- kg/m² (请填写身高和体重)";
                bmiDisplay.style.color = "var(--color-text-muted)";
                if (bmiHidden) bmiHidden.value = "";
            }
        }

        // 基础筛查身高体重
        var basicHeight = document.getElementById("basic-height");
        var basicWeight = document.getElementById("basic-weight");
        if (basicHeight) basicHeight.addEventListener("input", function () { calcBMI("basic"); });
        if (basicWeight) basicWeight.addEventListener("input", function () { calcBMI("basic"); });

        // 深度筛查身高体重
        var advHeight = document.getElementById("adv-height");
        var advWeight = document.getElementById("adv-weight");
        if (advHeight) advHeight.addEventListener("input", function () { calcBMI("advanced"); });
        if (advWeight) advWeight.addEventListener("input", function () { calcBMI("advanced"); });

        // 初始计算
        calcBMI("basic");
        calcBMI("advanced");

        // ================================================================
        // 随机填充示例数据
        // ================================================================
        function randomFill(tabId) {
            var idx = Math.floor(Math.random() * PROFILES.length);
            var p = PROFILES[idx];

            var isBasic = tabId === "tab-basic";
            var prefix = isBasic ? "basic" : "adv";

            // 年龄
            var ageEl = document.getElementById(prefix + "-age");
            if (ageEl) ageEl.value = p.age;

            // 性别
            var genderVal = isBasic ? p.genderVal : p.genderAdvVal;
            var genderRadios = document.querySelectorAll("#" + tabId + ' input[name="' + (isBasic ? "gender" : "gender_adv") + '"]');
            genderRadios.forEach(function (r) {
                r.checked = (r.value === genderVal);
            });

            // HbA1c
            var hba1cEl = document.getElementById(prefix + "-hba1c");
            if (hba1cEl) hba1cEl.value = p.hba1c;

            // 空腹血糖
            var fpgEl = document.getElementById(prefix + "-fpg");
            if (fpgEl) fpgEl.value = p.fastingGlucose;

            // 身高/体重
            var hEl = document.getElementById(prefix + "-height");
            var wEl = document.getElementById(prefix + "-weight");
            if (hEl) hEl.value = p.height;
            if (wEl) wEl.value = p.weight;
            calcBMI(isBasic ? "basic" : "advanced");

            // 进阶字段 (仅深度筛查)
            if (!isBasic) {
                setIfExists("adv-homa_ir", p.homaIr);
                setIfExists("adv-egfr", p.egfr);
                setIfExists("adv-urdact", p.urdact);
                setIfExists("adv-bp_sys", p.bpSys);
                setIfExists("adv-bp_dia", p.bpDia);
                setIfExists("adv-triglyc", p.triglyc);
                setIfExists("adv-ggt", p.ggt);
                setIfExists("adv-uric_acid", p.uricAcid);
                setIfExists("adv-alt", p.alt);
                setIfExists("adv-vit_d3", p.vitD3);
            }

            // Toast 提示
            showToast("已填充：" + p.label);
        }

        function setIfExists(id, val) {
            var el = document.getElementById(id);
            if (el) el.value = val;
        }

        // Toast 通知
        function showToast(msg) {
            var existing = document.querySelector(".toast-msg");
            if (existing) existing.remove();

            var toast = document.createElement("div");
            toast.className = "toast-msg";
            toast.textContent = msg;
            document.body.appendChild(toast);

            // 触发动画
            requestAnimationFrame(function () {
                toast.classList.add("toast-msg-show");
            });

            setTimeout(function () {
                toast.classList.remove("toast-msg-show");
                setTimeout(function () { toast.remove(); }, 300);
            }, 1800);
        }

        // 绑定随机填充按钮
        var basicRandomBtn = document.getElementById("random-fill-basic");
        var advRandomBtn = document.getElementById("random-fill-advanced");
        if (basicRandomBtn) basicRandomBtn.addEventListener("click", function () { randomFill("tab-basic"); });
        if (advRandomBtn) advRandomBtn.addEventListener("click", function () { randomFill("tab-advanced"); });

        // ================================================================
        // 客户端结果渲染 (对齐 miniapp/components/result-card)
        // ================================================================
        function renderResultCard(result) {
            var cfg = LEVEL_CONFIG[result.risk_level_code] || LEVEL_CONFIG[1];
            var barWidth = Math.min(result.risk_probability, 100);

            return (
                '<div class="result-card">' +
                '<h2>筛查评估报告</h2>' +
                '<div class="result-body" style="background:' + cfg.bg + '; border:1.5px solid ' + result.risk_color + ';">' +
                '<p class="risk-level-text" style="color:' + result.risk_color + ';">' +
                cfg.icon + ' ' + result.risk_level +
                '</p>' +
                '<p class="prob-number" style="color:' + result.risk_color + ';">' +
                result.risk_probability + '%</p>' +
                '<p class="prob-label">糖尿病风险概率</p>' +
                '<div class="bar-bg">' +
                '<div class="bar-fill" style="width:' + barWidth + '%; background:' + result.risk_color + ';"></div>' +
                '</div>' +
                '<p class="advice-text">' + result.advice + '</p>' +
                '<hr>' +
                '<small>模型 AUC: ' + result.model_auc + ' &nbsp;|&nbsp; ' +
                '筛查阈值: ' + result.threshold_pct + '% &nbsp;|&nbsp; ' +
                result.data_source + '</small>' +
                '<small>⚠ 本工具仅供筛查参考，不构成医疗诊断。请咨询专业医生。</small>' +
                '</div>' +
                '</div>'
            );
        }

        // ================================================================
        // 通用表单提交
        // ================================================================
        var loadingOverlay = document.getElementById("loading-overlay");

        function showLoading() {
            if (loadingOverlay) loadingOverlay.classList.remove("hidden");
        }

        function hideLoading() {
            if (loadingOverlay) loadingOverlay.classList.add("hidden");
        }

        /**
         * 将表单数据转为 JSON 对象
         */
        function formToJSON(form) {
            var data = {};
            var elements = form.querySelectorAll("input, select");
            elements.forEach(function (el) {
                if (el.type === "radio") {
                    if (el.checked) data[el.name] = el.value;
                } else if (el.type === "number") {
                    data[el.name] = el.value === "" ? null : parseFloat(el.value);
                } else if (el.tagName === "SELECT") {
                    data[el.name] = el.value;
                } else if (el.type === "hidden") {
                    data[el.name] = el.value === "" ? null : parseFloat(el.value);
                } else {
                    data[el.name] = el.value;
                }
            });

            // 基础筛查：从身高体重计算 BMI
            if (form.id === "form-basic") {
                var bmiHidden = document.getElementById("basic-bmi-hidden");
                if (bmiHidden && bmiHidden.value) {
                    data.bmi = parseFloat(bmiHidden.value);
                }
            }

            // 深度筛查：从身高体重计算 BMI
            if (form.id === "form-advanced") {
                var bmiHidden2 = document.getElementById("advanced-bmi-hidden");
                if (bmiHidden2 && bmiHidden2.value) {
                    data.bmi = parseFloat(bmiHidden2.value);
                }
            }

            return data;
        }

        /**
         * 显示客户端渲染的结果
         */
        function renderResult(containerId, resultData) {
            var container = document.getElementById(containerId);
            container.innerHTML = renderResultCard(resultData);
            container.classList.remove("hidden");
            setTimeout(function () {
                container.scrollIntoView({ behavior: "smooth", block: "nearest" });
            }, 100);
        }

        /**
         * 显示错误信息
         */
        function showError(containerId, message) {
            var container = document.getElementById(containerId);
            container.innerHTML =
                '<div class="result-card" style="border-left: 4px solid var(--color-danger);">' +
                '<h3 style="color:var(--color-danger); text-align:center;">⚠ 请求失败</h3>' +
                '<p style="text-align:center; color:var(--color-text-secondary); margin-top:10px;">' +
                message + '</p>' +
                '</div>';
            container.classList.remove("hidden");
        }

        /**
         * 客户端输入校验 (对齐 miniapp/utils/validator.js)
         */
        function validateForm(payload) {
            var errors = [];
            if (payload.age != null) {
                if (isNaN(payload.age)) errors.push("年龄格式不正确");
                else if (payload.age < 8) errors.push("年龄不能低于 8");
                else if (payload.age > 80) errors.push("年龄不能超过 80");
            }
            if (payload.hba1c != null) {
                if (isNaN(payload.hba1c)) errors.push("HbA1c 格式不正确");
                else if (payload.hba1c < 3) errors.push("HbA1c 不能低于 3.0");
                else if (payload.hba1c > 18) errors.push("HbA1c 不能超过 18.0");
            }
            if (payload.fasting_glucose != null) {
                if (isNaN(payload.fasting_glucose)) errors.push("空腹血糖格式不正确");
                else if (payload.fasting_glucose < 2.5) errors.push("空腹血糖不能低于 2.5");
                else if (payload.fasting_glucose > 30) errors.push("空腹血糖不能超过 30.0");
            }
            if (payload.bmi == null || payload.bmi === "" || isNaN(payload.bmi) || payload.bmi <= 0) {
                errors.push("请填写身高和体重以计算 BMI");
            } else if (payload.bmi < 12) {
                errors.push("BMI 不能低于 12");
            } else if (payload.bmi > 65) {
                errors.push("BMI 不能超过 65");
            }
            return errors;
        }

        /**
         * 绑定表单提交事件
         */
        function bindForm(formId, apiPath, resultContainerId) {
            var form = document.getElementById(formId);
            if (!form) return;

            var btn = form.querySelector(".btn-primary");
            var originalText = btn ? btn.textContent : "提交";

            form.addEventListener("submit", function (e) {
                e.preventDefault();

                var payload = formToJSON(form);

                // 客户端校验
                var errors = validateForm(payload);
                if (errors.length > 0) {
                    showError(resultContainerId, errors.join("; "));
                    return;
                }

                if (btn) {
                    btn.disabled = true;
                    btn.textContent = "分析中...";
                }
                showLoading();

                fetch(apiPath, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                })
                    .then(function (resp) {
                        if (!resp.ok) {
                            return resp.json().then(function (err) {
                                throw new Error(err.message || "服务器错误 (HTTP " + resp.status + ")");
                            });
                        }
                        return resp.json();
                    })
                    .then(function (body) {
                        hideLoading();
                        if (btn) {
                            btn.disabled = false;
                            btn.textContent = originalText;
                        }
                        // API 返回 { code: 0, message: "success", data: {...} }
                        if (body.code === 0 && body.data) {
                            renderResult(resultContainerId, body.data);
                        } else {
                            throw new Error(body.message || "响应数据异常");
                        }
                    })
                    .catch(function (err) {
                        hideLoading();
                        if (btn) {
                            btn.disabled = false;
                            btn.textContent = originalText;
                        }
                        showError(resultContainerId, err.message);
                    });
            });
        }

        // 绑定两个筛查表单
        bindForm("form-basic", "/api/predict/basic", "result-basic");
        bindForm("form-advanced", "/api/predict/advanced", "result-advanced");
    });
})();
