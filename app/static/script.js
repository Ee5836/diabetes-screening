/**
 * 糖尿病风险筛查工具 - 前端交互脚本
 * ========================================
 * 标签页切换 / 表单提交 / 结果渲染
 */

document.addEventListener("DOMContentLoaded", function () {

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
                // 切换标签时平滑滚动到表单顶部
                target.scrollIntoView({ behavior: "smooth", block: "start" });
            }
        });
    });

    // ================================================================
    // 通用表单提交处理
    // ================================================================
    var loadingOverlay = document.getElementById("loading-overlay");

    function showLoading() {
        loadingOverlay.classList.remove("hidden");
    }

    function hideLoading() {
        loadingOverlay.classList.add("hidden");
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
            } else {
                data[el.name] = el.value;
            }
        });
        return data;
    }

    /**
     * 渲染后端返回的 HTML 结果
     */
    function renderResult(containerId, html) {
        var container = document.getElementById(containerId);
        container.innerHTML = '<div class="result-card">' + html + '</div>';
        container.classList.remove("hidden");
        // 平滑滚动到结果卡片
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
            '<div class="result-card" style="border-left: 4px solid #D4756B;">' +
            '<h3 style="color:#D4756B; text-align:center;">⚠ 请求失败</h3>' +
            '<p style="text-align:center; color:#8E8984; margin-top:10px;">' + message + '</p>' +
            '</div>';
        container.classList.remove("hidden");
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

            if (btn) {
                btn.disabled = true;
                btn.textContent = "分析中...";
            }
            showLoading();

            var payload = formToJSON(form);

            fetch(apiPath, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            })
                .then(function (resp) {
                    if (!resp.ok) {
                        return resp.json().then(function (err) {
                            throw new Error(err.error || "服务器错误 (HTTP " + resp.status + ")");
                        });
                    }
                    return resp.json();
                })
                .then(function (data) {
                    hideLoading();
                    if (btn) {
                        btn.disabled = false;
                        btn.textContent = originalText;
                    }
                    renderResult(resultContainerId, data.result_html);
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
    bindForm("form-basic",   "/api/predict/basic",    "result-basic");
    bindForm("form-advanced","/api/predict/advanced", "result-advanced");
});
