from flask import Flask, render_template, request, make_response, send_file
from rembg import remove, new_session
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from apng import APNG
from io import BytesIO
import os
import math
import io
from werkzeug.utils import secure_filename

REMBG_MODEL = os.getenv("REMBG_MODEL", "silueta")  # 軽量モデル
_session = None

def remove_bg(input_bytes: bytes) -> bytes:
    global _session
    if _session is None:
        _session = new_session(REMBG_MODEL)
    return remove(input_bytes, session=_session)

app = Flask(__name__)
UPLOAD_FOLDER = os.path.join(os.getcwd(), "static", "safe_uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
FONT_PATH = "font/GenEiPOPle-Bk.ttf"

@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html")

@app.route("/preview_static")
def preview_static():
    filename = request.args.get("filename")
    return render_template("preview_static.html", filename=filename)

@app.route("/create_static", methods=["POST"])
def create_static():
    file = request.files["image"]
    text = request.form.get("text", "")
    size = request.form.get("size", "stamp")  # 'stamp' | 'mini' | 'both'

    filename = secure_filename(file.filename)
    basename, _ = os.path.splitext(filename)
    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)

    with open(path, "rb") as f:
        input_data = f.read()

    # 背景除去など、既存の前処理を通す
    output_data = remove(input_data)
    src = Image.open(io.BytesIO(output_data)).convert("RGBA")

    def render_static(src_img: Image.Image, W: int, H: int, *,
                      margin_top: int, margin_bottom: int,
                      min_font: int, font_ratio: float, text_color=(0,0,0,255)) -> Image.Image:
        """静止スタンプ1枚を作る共通処理"""
        content_h = max(1, H - margin_top - margin_bottom)

        # 画像を幅W×高さcontent_h に合わせてアスペクト比維持でフィット（幅基準）
        resized = src_img.resize((W, content_h), Image.LANCZOS)

        canvas = Image.new("RGBA", (W, H), (255, 255, 255, 0))
        canvas.paste(resized, (0, margin_top))

        # 文字描画
        draw = ImageDraw.Draw(canvas)
        # 幅に対する割合でフォントサイズ決定
        dyn_size = max(min_font, int(W * font_ratio))
        try:
            font = ImageFont.truetype(FONT_PATH, size=dyn_size)
        except:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = max(0, (W - tw)//2)
        ty = max(0, margin_top - th//2)  # 画像の上辺あたりに重ならない位置

        draw.text((tx, ty), text, font=font, fill=text_color)
        return canvas

    # ---- 分岐して生成 ----
    if size in ("stamp", "mini"):
        if size == "stamp":
            W, H = 370, 320
            img = render_static(src, W, H, margin_top=40, margin_bottom=0,
                                min_font=24, font_ratio=1/12)
        else:  # mini
            W, H = 96, 74
            img = render_static(src, W, H, margin_top=12, margin_bottom=0,
                                min_font=10, font_ratio=1/9)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        resp = make_response(send_file(
            buf, mimetype="image/png", as_attachment=True,
            download_name=f"{basename}_static_{size}_{W}x{H}.png"
        ))
        resp.headers["Cache-Control"] = "no-store"
        return resp

    else:  # size == 'both' → ZIPで両方返却
        from zipfile import ZipFile, ZIP_DEFLATED
        # 370x320
        img1 = render_static(src, 370, 320, margin_top=40, margin_bottom=0,
                             min_font=24, font_ratio=1/12)
        b1 = io.BytesIO(); img1.save(b1, format="PNG"); b1 = b1.getvalue()
        # 96x74
        img2 = render_static(src, 96, 74, margin_top=12, margin_bottom=0,
                             min_font=10, font_ratio=1/9)
        b2 = io.BytesIO(); img2.save(b2, format="PNG"); b2 = b2.getvalue()

        zbuf = io.BytesIO()
        with ZipFile(zbuf, "w", compression=ZIP_DEFLATED) as z:
            z.writestr(f"{basename}_static_stamp_370x320.png", b1)
            z.writestr(f"{basename}_static_mini_96x74.png", b2)
        zbuf.seek(0)

        resp = make_response(send_file(
            zbuf, mimetype="application/zip", as_attachment=True,
            download_name=f"{basename}_static_both.zip"
        ))
        resp.headers["Cache-Control"] = "no-store"
        return resp
@app.route("/preview_animation")
def preview_animation():
    filename = request.args.get("filename")
    return render_template("preview_animation.html", filename=filename)

@app.route("/create_animation", methods=["POST"])
def create_animation():
    print("★ create_animation called")
    file = request.files["image"]#フォームからアップロードされたファイルを取得する
    text = request.form.get("text", "")
    anim_type = request.form.get("anim_type", "pulsing")
    variant  = request.form.get("variant", "main")  # ← 'main' or 'stamp'
    base_font_size = 24

    safe_name = secure_filename(file.filename or "upload")
    basename, ext = os.path.splitext(safe_name)
    input_data = file.read()
    output_data = remove_bg(input_data)
    img = Image.open(io.BytesIO(output_data)).convert("RGBA")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    # ----- サイズ分岐（variantで切替） -----
    if variant == "stamp":
        STAMP_WIDTH, STAMP_HEIGHT = 320, 270
    else:
        STAMP_WIDTH, STAMP_HEIGHT = 240, 240

    margin_top = 40
    content_height = STAMP_HEIGHT - margin_top

    # 画像リサイズ（縦横比維持）
    original_w, original_h = img.size
    aspect_ratio = original_w / original_h
    if original_w > original_h:
        new_w = STAMP_WIDTH
        new_h = int(STAMP_WIDTH / aspect_ratio)
    else:
        new_h = content_height
        new_w = int(content_height * aspect_ratio)

    resized_img = img.resize((new_w, new_h), Image.LANCZOS).convert("RGBA")  # 念のためRGBAへ
    base_img = Image.new("RGBA", (STAMP_WIDTH, content_height), (255, 255, 255, 0))
    x = (STAMP_WIDTH - new_w) // 2
    y = (content_height - new_h) // 2
    base_img.paste(resized_img, (x, y), mask=resized_img.split()[3])

    # ----- フレーム生成 -----
    frames = []
    loop_count = 0  # 既定（0=無限ループ）。必要に応じて1などに
    if anim_type == "pulsing":
        frame_count = 20
        scales = [1.0] * frame_count
        shifts_x = [0,4,-3,3,-4,4,-3,3,-4,4,-3,3,-4,4,-3,3,-4,4,-3,3]
        shifts_y = [0] * frame_count
        text_opacity = [255] * frame_count
        loop_count = 1
    elif anim_type == "slidein":
        frame_count = 20
        scales = [1.0] * frame_count
        shifts_x = [2*i for i in range(frame_count)]
        shifts_y = [0] * frame_count
        text_opacity = [255] * frame_count
        loop_count = 1
    elif anim_type == "bounce":
        frame_count = 20
        amplitude = 25
        scales = [1.0] * frame_count
        shifts_x = [0] * frame_count
        shifts_y = [int(math.sin(i / frame_count * math.pi * 2) * amplitude) for i in range(frame_count)]
        text_opacity = [255] * frame_count
        loop_count = 1
    elif anim_type == "blur":
        frame_count = 40
        scales = [1.0] * frame_count
        shifts_x = [0] * frame_count
        shifts_y = [0] * frame_count
        apply_blur = [False, True, True, True] * 10
        text_opacity = [255] * frame_count
        loop_count = 1
    elif anim_type == "rotate":
        frame_count = 6
        scales = [1.0] * frame_count
        shifts_x = [0] * frame_count
        shifts_y = [0] * frame_count
        rotations = [0, 72, 144, 216, 288, 360]
        text_opacity = [255] * frame_count
        loop_count = 1
    elif anim_type == "popup":
        frame_count = 20
        scales = [0.5,0.7,0.9,1.1,1.0,0.9,0.7,0.5,0.5,0.7,0.9,1.1,1.0,0.9,0.7,0.5,0.5,0.7,0.9,1.1]
        shifts_x = [0] * frame_count
        shifts_y = [0] * frame_count
        apply_blur = [False] * frame_count
        text_opacity = [255] * frame_count
        loop_count = 1
    elif anim_type == "flash":
        frame_count = 20
        scales = [1.0] * frame_count
        shifts_x = [0] * frame_count
        shifts_y = [0] * frame_count
        brightness = [0.3 if i % 2 == 0 else 2.0 for i in range(frame_count)]
        text_opacity = [255] * frame_count
        loop_count = 1
    else:
        frame_count = 2
        scales = [1.0] * frame_count
        shifts_x = [0] * frame_count
        shifts_y = [0] * frame_count
        text_opacity = [255] * frame_count
        loop_count = 1

    for i, (scale, shift_x, shift_y) in enumerate(zip(scales, shifts_x, shifts_y)):
        new_size = (int(base_img.width * scale), int(base_img.height * scale))
        resized = base_img.resize(new_size, Image.LANCZOS)

        if anim_type == "rotate":
            rotation_angle = rotations[i]
            resized = resized.rotate(rotation_angle, resample=Image.BICUBIC, expand=True)

        canvas = Image.new("RGBA", (STAMP_WIDTH, STAMP_HEIGHT), (255, 255, 255, 0))
        cx = (STAMP_WIDTH - resized.width) // 2 + shift_x
        cy = (STAMP_HEIGHT - resized.height) // 2 + shift_y
        canvas.paste(resized, (cx, cy), resized)

        draw = ImageDraw.Draw(canvas)
        try:
            dynamic_font_size = max(10, int(base_font_size * scale))
            font = ImageFont.truetype(FONT_PATH, size=dynamic_font_size)
        except:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        text_x = (STAMP_WIDTH - text_w) // 2 + shift_x
        text_y = 40 + shift_y
        if text_y < 0: text_y = 0
        draw.text((text_x, text_y), text, font=font, fill=(0, 0, 0, text_opacity[i]))

        if anim_type == "blur":
            try:
                if apply_blur[i]:
                    canvas = canvas.filter(ImageFilter.GaussianBlur(radius=2))
            except NameError:
                pass

        if anim_type == "flash":
            enhancer = ImageEnhance.Brightness(canvas)
            canvas = enhancer.enhance(brightness[i])

        frames.append(canvas)

    # ----- APNGとして保存（PNG+save_all） -----
    total_allowed_ms = 3000
    num_frames = max(2, len(frames))
    exact = total_allowed_ms / num_frames
    base_delay = int(exact)
    remainder = total_allowed_ms - (base_delay * num_frames)
    durations = [base_delay] * num_frames
    durations[-1] += remainder

    output = BytesIO()
    frames[0].save(
        output, format="PNG", save_all=True,
        append_images=frames[1:],
        duration=durations, loop=loop_count, disposal=2
    )
    output.seek(0)

    # APNGは多くの環境で image/png で配信します（必要なら image/apng に変更可）
    resp = make_response(send_file(
        output,
        mimetype="image/png",
        as_attachment=True,
        download_name=f"{basename}_anim_{variant}_{STAMP_WIDTH}x{STAMP_HEIGHT}.png"
    ))
    resp.headers["Cache-Control"] = "no-store"
    return resp         
if __name__ == "__main__":
    app.run()


