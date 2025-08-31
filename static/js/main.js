document.addEventListener("DOMContentLoaded", () => {
  // 共通: 要素取得の小ヘルパ
  const $ = (sel) => document.querySelector(sel);

  // ------------------------------------------------------------
  // ③ メイン画像: /create_main
  // ------------------------------------------------------------
  const mainForm = $("#main-form");
  if (mainForm) {
    const loadingMessage = $("#loading-message");
    mainForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const fileInput = $("#main-image");
      const textInput = $("#main-text");
      if (!fileInput?.files[0] || !textInput?.value.trim()) {
        alert("画像とテキストを入力してください。");
        return;
      }

      const fd = new FormData(mainForm);
      const variant = fd.get("variant") || "main"; // 'main' | 'stamp'

      try {
        if (loadingMessage) loadingMessage.style.display = "block";

        const res = await fetch("/create_main", { method: "POST", body: fd });
        if (!res.ok) throw new Error("メイン画像の生成に失敗しました");

        const blob = await res.blob();
        const url = URL.createObjectURL(blob);

        const img  = $("#main-preview-image");
        const link = $("#main-download-link");
        if (img) {
          img.src = url;
          img.style.display = "block";
        }
        if (link) {
          link.href = url;
          const name = (variant === "stamp") ? "main_370x320.png" : "main_240x240.png";
          link.download = name;
          link.style.display = "inline";
        }
      } catch (err) {
        alert("エラー: " + (err?.message || "不明なエラー"));
      } finally {
        if (loadingMessage) loadingMessage.style.display = "none";
      }
    });
  }

  // ------------------------------------------------------------
  // ① 静止画スタンプ: /create_static
  // ------------------------------------------------------------
  const staticForm = $("#static-form");
  if (staticForm) {
    const loadingMessage = $("#loading-message");
    staticForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const fileInput = $("#static-form input[type='file']");
      const textInput = $("#static-form input[type='text']");
      const previewImg = $("#preview-image");
      const downloadLink = $("#download-link");

      if (!fileInput?.files[0] || !textInput?.value.trim()) {
        alert("画像とテキストを入力してください。");
        return;
      }

      const fd = new FormData(staticForm); // ← ラジオの size も一緒に送る
      const size = fd.get("size") || "stamp"; // 'stamp' | 'mini' | 'both'

      try {
        if (loadingMessage) loadingMessage.style.display = "block";

        const res = await fetch("/create_static", { method: "POST", body: fd });
        if (!res.ok) throw new Error("画像生成に失敗しました");

        // size=both のときは ZIP になる想定
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);

        if (size === "both") {
          // プレビューはせずダウンロードのみ
          if (downloadLink) {
            downloadLink.href = url;
            downloadLink.download = "static_both.zip";
            downloadLink.style.display = "inline";
          }
          if (previewImg) previewImg.style.display = "none";
        } else {
          // プレビュー表示
          if (previewImg) {
            previewImg.src = url;
            previewImg.style.display = "block";
          }
          if (downloadLink) {
            const name =
              size === "mini" ? "static_96x74.png" :
              "static_370x320.png";
            downloadLink.href = url;
            downloadLink.download = name;
            downloadLink.style.display = "inline";
          }
        }
      } catch (err) {
        alert("エラー: " + (err?.message || "不明なエラー"));
      } finally {
        if (loadingMessage) loadingMessage.style.display = "none";
      }
    });
  }

  // ------------------------------------------------------------
  // ② アニメーション種類選択ボタン (.anim-btn)
  // ------------------------------------------------------------
  const hiddenType = $("#anim_type");
  const animButtons = document.querySelectorAll(".anim-btn");
  if (hiddenType && animButtons.length) {
    animButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        animButtons.forEach((b) => b.classList.remove("selected"));
        btn.classList.add("selected");
        hiddenType.value = btn.getAttribute("data-value") || "";
      });
    });
    // デフォルトで最初を選択（未選択対策）
    if (!hiddenType.value && animButtons[0]) {
      animButtons[0].classList.add("selected");
      hiddenType.value = animButtons[0].getAttribute("data-value") || "";
    }
  }

  // ------------------------------------------------------------
  // ③ アニメ画像: /create_animation
  // ------------------------------------------------------------
  const animForm = $("#anim-form");
  if (animForm) {
    const loadingMessage = $("#loading-message");
    const hiddenInput = $("#anim_type");

    animForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const fileInput = $("#anim-image");
      const textInput = $("#anim-text");
      const typeValue = hiddenInput ? hiddenInput.value : "";

      if (!fileInput?.files[0] || !textInput?.value.trim() || !typeValue) {
        alert("画像・テキスト・アニメーションの種類を必ず選択してください。");
        return;
      }

      const fd = new FormData(animForm); // variant も一緒に POST
      const variant = fd.get("variant") || "main"; // 'main' | 'stamp'

      try {
        if (loadingMessage) loadingMessage.style.display = "block";

        const res = await fetch("/create_animation", { method: "POST", body: fd });
        if (!res.ok) throw new Error("アニメーション生成に失敗しました");

        const blob = await res.blob();
        const url = URL.createObjectURL(blob);

        const img = $("#preview-image");
        const link = $("#download-link");
        if (img) {
          img.src = url;
          img.style.display = "block";
        }
        if (link) {
          const name = (variant === "stamp")
            ? "animated_stamp_370x320.png"  // APNG でも image/png で来る想定
            : "animated_main_240x240.png";
          link.href = url;
          link.download = name;
          link.style.display = "inline";
        }
      } catch (err) {
        alert("エラー: " + (err?.message || "不明なエラー"));
      } finally {
        if (loadingMessage) loadingMessage.style.display = "none";
      }
    });
  }
});
