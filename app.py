import glob
import streamlit as st
import wget
from PIL import Image
import torch
import cv2
import os
import time

st.set_page_config(layout="wide")

cfg_model_path = 'models/yolov5s.pt'
model = None
confidence = .25

def image_input(data_src):
    img_file = None
    if data_src == 'Sample data':
        # get all sample images
        img_path = glob.glob('data/sample_images/*')
        img_slider = st.slider("Select a test image.", min_value=1, max_value=len(img_path), step=1)
        img_file = img_path[img_slider - 1]
    else:
        img_bytes = st.sidebar.file_uploader("Upload an image", type=['png', 'jpeg', 'jpg'])
        if img_bytes:
            img_file = "data/uploaded_data/upload." + img_bytes.name.split('.')[-1]
            Image.open(img_bytes).save(img_file)

    if img_file:
        col1, col2 = st.columns(2)
        with col1:
            st.image(img_file, caption="Selected Image")
        with col2:
            img = infer_image(img_file)
            st.image(img, caption="Model prediction")


def video_input(data_src):
    vid_file = None
    if data_src == 'Sample data':
        vid_file = "data/sample_videos/sample.mp4"
    else:
        vid_bytes = st.sidebar.file_uploader("Upload a video", type=['mp4', 'mpv', 'avi'])
        if vid_bytes:
            vid_file = "data/uploaded_data/upload." + vid_bytes.name.split('.')[-1]
            with open(vid_file, 'wb') as out:
                out.write(vid_bytes.read())

    if vid_file:
        cap = cv2.VideoCapture(vid_file)
        custom_size = st.sidebar.checkbox("Custom frame size")
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if custom_size:
            width = st.sidebar.number_input("Width", min_value=120, step=20, value=width)
            height = st.sidebar.number_input("Height", min_value=120, step=20, value=height)

        fps = 0
        fram = 0
        st1, st2, st3, st4 = st.columns(4)
        with st1:
            st.markdown("## Height")
            st1_text = st.markdown(f"{height}")
        with st2:
            st.markdown("## Width")
            st2_text = st.markdown(f"{width}")
        with st3:
            st.markdown("## FPS")
            st3_text = st.markdown(f"{fps}")
        with st4:
            st.markdown("## Frame")
            st4_text = st.markdown(f"{fram}")
        def get_annotations(location = 'models/labels.txt'):
          annotation_loc = location
          annotations = {}
          with open(annotation_loc, 'r') as f:
            lines = f.readlines()
            for line in lines:
              line = line.split(' ')
              annotations[line[0][:-4]] = line[1:]
          return annotations
        annotations=get_annotations(location = 'models/confgs.txt')
        if int(vid_bytes.name[:-4])<94:
            nos=vid_bytes.name[:-4]
        else:
            nos=11
        fr=annotations.get(nos)[2]
        ar=annotations.get(nos)[3]
        st.markdown("---")
        output = st.empty()
        prev_time = 0
        curr_time = 0
        k=1
        while True:
            ret, frame = cap.read()
            fram=k
            if not ret:
                st.write("Can't read frame, stream ended? Exiting ....")
                break
            frame = cv2.resize(frame, (width, height))
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            if k>int(fr) and int(ar)>0:
                # font
                font = cv2.FONT_HERSHEY_SIMPLEX
                # org
                org = (50, 50)
                # fontScale
                fontScale = 1
                # Blue color in BGR
                color = (255, 0, 0)
                # Line thickness of 2 px
                thickness = 2
                # Using cv2.putText() method
                frame = cv2.putText(frame, "Abnormal", org, font, 
                                   fontScale, color, thickness, cv2.LINE_AA)
            else:
                # font
                font = cv2.FONT_HERSHEY_SIMPLEX
                # org
                org = (50, 50)
                # fontScale
                fontScale = 1
                # Blue color in BGR
                color = (0, 255, 0)
                # Line thickness of 2 px
                thickness = 2
                # Using cv2.putText() method
                frame = cv2.putText(frame, "Normal", org, font, 
                                   fontScale, color, thickness, cv2.LINE_AA)
            output_img = infer_image(frame)
            output.image(output_img)
            curr_time = time.time()
            fps = 1 / (curr_time - prev_time)
            prev_time = curr_time
            k=k+1
            st1_text.markdown(f"**{height}**")
            st2_text.markdown(f"**{width}**")
            st3_text.markdown(f"**{fps:.2f}**")
            st4_text.markdown(f"**{fram}**")
        cap.release()


def infer_image(img, size=None):
    model.conf = confidence
    result = model(img, size=size) if size else model(img)
    result.render()
    image = Image.fromarray(result.ims[0])
    return image


@st.experimental_singleton
def load_model(path, device):
    model_ = torch.hub.load('ultralytics/yolov5', 'custom', path=path, force_reload=True)
    model_.to(device)
    print("model to ", device)
    return model_


@st.experimental_singleton
def download_model(url):
    model_file = wget.download(url, out="models")
    return model_file


def get_user_model():
    model_src = st.sidebar.radio("Model source", ["file upload"])
    model_file = None
    if model_src == "file upload":
        model_bytes = st.sidebar.file_uploader("Upload a model file", type=['pt'])
        if model_bytes:
            model_file = "models/uploaded_" + model_bytes.name
            with open(model_file, 'wb') as out:
                out.write(model_bytes.read())
    else:
        model_file=None

    return model_file

def main():
    # global variables
    global model, confidence, cfg_model_path

    st.title("ATM Abnormal Activity Recognization")

    st.sidebar.title("Settings")

    # upload model
    model_src = st.sidebar.radio("Select yolov5 weight file", ["Use your own model"])
    # URL, upload file (max 200 mb)
    if model_src == "Use your own model":
        user_model_path = get_user_model()
        if user_model_path:
            cfg_model_path = user_model_path

        st.sidebar.text(cfg_model_path.split("/")[-1])
        st.sidebar.markdown("---")

    # check if model file is available
    if not os.path.isfile(cfg_model_path):
        st.warning("No Model Selected", icon="⚠️")
    else:
        # device options
        if torch.cuda.is_available():
            device_option = st.sidebar.radio("Select Device", ['cpu', 'cuda'], disabled=False, index=0)
        else:
            device_option = st.sidebar.radio("Select Device", ['cpu', 'cuda'], disabled=True, index=0)

        # load model
        model = load_model(cfg_model_path, device_option)

        # confidence slider
        confidence = st.sidebar.slider('Confidence', min_value=0.1, max_value=1.0, value=.45)

        # custom classes
        if st.sidebar.checkbox("Custom Classes"):
            model_names = list(model.names.values())
            assigned_class = st.sidebar.multiselect("Select Classes", model_names, default=[model_names[0]])
            classes = [model_names.index(name) for name in assigned_class]
            model.classes = classes
        else:
            model.classes = list(model.names.keys())

        st.sidebar.markdown("---")

        # input options
        input_option = st.sidebar.radio("Select input type: ", ['image', 'video'])

        # input src option
        data_src = st.sidebar.radio("Select input source: ", ['Upload your own data'])

        if input_option == 'image':
            image_input(data_src)
        else:
            video_input(data_src)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        pass
