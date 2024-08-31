import io
import json
import piexif
import streamlit as st
from PIL import Image, ImageFilter, ImageDraw, ImageFont

def download_img(new_img):
    # 将图像保存到内存中
    img_byte_arr = io.BytesIO()
    new_img.save(img_byte_arr, format='JPEG')
    img_byte_arr = img_byte_arr.getvalue()
    
    # 提供下载按钮
    st.download_button(
        label="保存图像",
        data=img_byte_arr,
        file_name="output.jpg",
        mime="image/jpeg"
    )

def add_rounded_corners(img, radius):
    # 创建一个圆角遮罩
    mask = Image.new('L', img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), img.size], radius=radius, fill=255)
    # 创建一个新的图像，大小与原图相同，背景透明
    corners_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
    # 将原图粘贴到新的图像上，并使用圆角遮罩
    corners_img.paste(img, (0, 0), mask=mask)
    return corners_img

def add_rounded_shadow(img, radius):
    width, height = img.size
    min_size = min(width, height)
    shadow_width, shadow_height = int(width + 0.1 * min_size), int(height + 0.1 * min_size)
    # 创建遮罩
    mask = Image.new('L', [shadow_width, shadow_height], 0)
    draw = ImageDraw.Draw(mask)
    for i in range(radius):
        alpha = int(255 * (i / radius))
        draw.rounded_rectangle(
            [i, i, shadow_width - i, shadow_height - i],
            radius=radius - i,
            outline=alpha,
            width=1
        )
    
    # 创建全黑的图片
    black_img = Image.new('RGBA', [shadow_width, shadow_height], (50, 50, 50, 255))
    
    # 将全黑的图片粘贴到阴影图像上
    shadow_img = Image.new('RGBA', [shadow_width, shadow_height], (0, 0, 0, 0))
    shadow_img.paste(black_img, (0, 0), mask=mask)
    
    return shadow_img

def add_border_and_text(img, exif_data,font_path,font_size, scale_factor, fuzziness):
    # 获取原图尺寸
    width, height = img.size
    min_size=min(width, height)
    # 读取EXIF数据
    if exif_data==None:
        try:
            exif_data = piexif.load(img.info['exif'])
            camera_model = exif_data['0th'][piexif.ImageIFD.Model].decode('utf-8').strip('\x00')
            iso = exif_data['Exif'][piexif.ExifIFD.ISOSpeedRatings]
            focal_length = exif_data['Exif'][piexif.ExifIFD.FocalLengthIn35mmFilm]
            aperture = exif_data['Exif'][piexif.ExifIFD.FNumber]
            aperture=aperture[0]/aperture[1]
            shutter_speed = exif_data['Exif'][piexif.ExifIFD.ExposureTime]
            shutter_speed=round(shutter_speed[1]/shutter_speed[0])
        except:
            st.write('自动获取照片信息失败，请手动输入')
            camera_model = 'None'
            iso = 100
            focal_length = 50
            aperture = 1.8
            shutter_speed=0.1
    else:
        try:
            camera_model = exif_data[0]
            iso = exif_data[1]
            focal_length = exif_data[2]
            aperture = exif_data[3]
            try:
                shutter_speed = round(1/float(exif_data[4]))
            except:
                try:
                    speed_up=float(exif_data[4].split('/')[0])
                    speed_down=float(exif_data[4].split('/')[1])
                    shutter_speed = round(speed_down/speed_up)
                except:
                    shutter_speed=1.0
        except:
            st.write('请输入完整的照片信息')
            camera_model = 'None'
            iso = 100
            focal_length = 50
            aperture = 1.8
            shutter_speed=0.1

    img = img.convert("RGBA")
    # 创建模糊背景
    blurred_img = img.filter(ImageFilter.GaussianBlur(fuzziness))
    radius=int(width/10)
    corners_img = add_rounded_corners(img, radius)
    shadow_img=add_rounded_shadow(img, radius)
    blurred_img = blurred_img.resize((int(width+min_size * (scale_factor-1.0)), int(height +min_size *( scale_factor-1.0))))
    # 创建一个临时图像用于粘贴
    temp_img = Image.new('RGBA', blurred_img.size, (0, 0, 0, 0))
    temp_img.paste(shadow_img, (int((blurred_img.width - shadow_img.width) / 2), int((blurred_img.height - shadow_img.height) / 2)))
    # 先将 shadow_img 粘贴到 blurred_img 上
    blurred_img = Image.alpha_composite(blurred_img, temp_img)
    # 再将 corners_img 粘贴到结果图像上
    blurred_img.paste(corners_img, (int((blurred_img.width - img.width) / 2), int((blurred_img.height - img.height) / 2)), mask=corners_img)
    # 添加文本
    draw = ImageDraw.Draw(blurred_img)
    font_camera = ImageFont.truetype(font_path, int(1.2/100 * width * font_size))
    font = ImageFont.truetype(font_path, int(1/100 * width * font_size))
    
    camera_text = f"{camera_model}"
    bbox = draw.textbbox((0, 0), camera_text, font=font_camera)
    camera_text_width, camera_text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
    camera_text_position = ((blurred_img.width - camera_text_width) / 2, (blurred_img.height + shadow_img.height) / 2+0.1*camera_text_height)
    draw.text(camera_text_position, camera_text, fill="white", font=font_camera)
    
    text = f"ISO{iso} {focal_length}mm f/{aperture} 1/{shutter_speed}s"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
    text_position = ((blurred_img.width - text_width) / 2, (blurred_img.height + shadow_img.height) / 2+1.1*camera_text_height+text_height)
    draw.text(text_position, text, fill="white", font=font)
    # 转换为RGB模式
    blurred_img = blurred_img.convert("RGB")
    return blurred_img

st.set_page_config(
    page_title="照片水印",
    page_icon="📷",
    layout="wide",
    initial_sidebar_state="expanded")
# Main page heading
st.title("📷照片水印")

# 从JSON文件中读取品牌和型号信息
with open('devices.json', 'r', encoding='utf-8') as f:
    devices = json.load(f)

# 从JSON文件中读取品牌和型号信息
with open('fonts.json', 'r', encoding='utf-8') as f:
    fonts = json.load(f)

camera_brands = devices["camera_brands"]
phone_brands = devices["phone_brands"]
font_type=fonts["fonts"]

exif_data_get = st.sidebar.radio("照片信息获取", ("自动获取","手动输入"))
if exif_data_get=="手动输入":
    # 选择相机或手机
    device_type = st.sidebar.radio("选择设备类型", ("相机", "手机"))

    if device_type == "相机":
        brand = st.sidebar.selectbox("相机品牌", list(camera_brands.keys()) + ["新品牌"])
        if brand == "新品牌":
            brand = st.sidebar.text_input("新品牌")
            model = st.sidebar.text_input("新型号")
        else:
            model = st.sidebar.selectbox("相机型号", camera_brands[brand] + ["新型号"])
            if model == "新型号":
                model = st.sidebar.text_input("新型号")
            
    elif device_type == "手机":
        brand = st.sidebar.selectbox("相机品牌", list(phone_brands.keys()) + ["新品牌"])
        if brand == "新品牌":
            brand = st.sidebar.text_input("新品牌")
            model = st.sidebar.text_input("新型号")
        else:
            model = st.sidebar.selectbox("相机型号", phone_brands[brand] + ["新型号"])
            if model == "新型号":
                model = st.sidebar.text_input("新型号")
    exif_data=[]
    camera_model=brand+' '+model;exif_data.append(camera_model)
    iso = st.sidebar.text_input("感光度");exif_data.append(iso)
    focal_length=st.sidebar.text_input("焦距mm/等效全画幅");exif_data.append(focal_length)
    aperture=st.sidebar.text_input("光圈/f");exif_data.append(aperture)
    shutter_speed=st.sidebar.text_input("快门/s");exif_data.append(shutter_speed)
elif exif_data_get=="自动获取":
    exif_data=None

fonttype = st.sidebar.selectbox("水印字体类型", list(font_type.keys()))
font = st.sidebar.selectbox("水印字体", font_type[fonttype])
font_path='./fonts/'+fonttype+'/'+font+'.ttf'
scale_factor_font = float(st.sidebar.slider("选择字体大小与照片比例", 0.1, 1.0, 0.4))
scale_factor_filter=float(st.sidebar.slider("选择边框大小", 0.1, 1.0, 0.3))
fuzziness=float(st.sidebar.slider("边框模糊度", 0.1, 1.0, 0.5))
source_img = st.sidebar.file_uploader("选择图片...", type=("jpg", "jpeg", "png", 'bmp', 'webp'), accept_multiple_files=False)
col1, col2 = st.columns(2)
if source_img is None:
    with col1:
        default_image = Image.open('./images/default.jpg')
        st.image(default_image, caption="默认图像", use_column_width=True)
    with col2:
        default_detected_image = Image.open('./images/default_frame.jpg')
        st.image(default_detected_image, caption='添加水印后图片', use_column_width=True)
else:
    img = Image.open(source_img)
    with col1:
        st.image(img, caption="上传的图像", use_column_width=True)
    with col2:
        if exif_data_get=='自动获取':
            # exif_data=None
            if st.sidebar.button('添加边框'):
                new_img=add_border_and_text(img,exif_data,font_path,5*scale_factor_font,1.0+scale_factor_filter,1000*fuzziness)
                st.image(new_img, caption='添加边框后图片', use_column_width=True)
                download_img(new_img)
        elif exif_data_get=='手动输入':
            if st.sidebar.button('添加边框'):
                new_img=add_border_and_text(img,exif_data,font_path,5*scale_factor_font,1.0+scale_factor_filter,1000*fuzziness)
                st.image(new_img, caption='添加边框后图片', use_column_width=True)
                download_img(new_img)

# import os
# import json

# def get_files_in_directory(directory):
#     files = []
#     for filename in os.listdir(directory):
#         if os.path.isfile(os.path.join(directory, filename)):
#             files.append(os.path.splitext(filename)[0])
#     return files

# def save_to_json(directory, output_file):
#     files = get_files_in_directory(directory)
#     data = {"fonts": {"fonts": files}}
#     with open(output_file, 'w', encoding='utf-8') as f:
#         json.dump(data, f, ensure_ascii=False, indent=4)

# save_to_json("./fonts/en",'./en.json')