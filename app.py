from ultralytics import YOLO
from flask import Flask, jsonify, request, send_file
import os
from flask_cors import CORS
import cv2
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

def processingVideo(input_path, output_path):

    cap = cv2.VideoCapture(input_path)

    if not cap.isOpened():
        print("Unable to open input video")
        return False


    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0 or fps is None:
        fps = 30.0 

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    size = (width, height)
    model = YOLO('best.pt')


    fourcc = cv2.VideoWriter_fourcc(*'mp4v')


    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    out = cv2.VideoWriter(output_path, fourcc, fps, size)

    if not out.isOpened():
        print("Failed to open VideoWriter")
        return False

    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break


        results = model(frame)

        r = results[0]
        annotated_frame = results[0].plot()

        for box in r.boxes:

            cls_id = int(box.cls)
            conf = round(float(box.conf) * 100, 1)

            if r.names[cls_id] == 'Kidnap' and round(float(box.conf) * 100, 1) > 70:
                print('KIDNAPPING FOUND PLEASE SEND MAIL TO POLICE')
                cv2.imwrite("./uploads/most_suspicious_frame.jpg", annotated_frame.copy())
                return True

            print({
                "class": r.names[cls_id],
                "confidence": f"{conf}%",
                "bbox": box.xyxy[0].tolist()
            })

        out.write(annotated_frame)
        frame_count += 1

    cap.release()
    out.release()

    if os.path.exists(output_path):

        print(f"Processed {frame_count} frames")
        print(f"Output saved successfully: {output_path}")
        return True
    
    else:
        print("Output file not created")
        return False


@app.route('/')
def home_route():

    response = {
        "status": True,
        "response": "secure circle backend is up and running"
    }

    return jsonify(response), 200


@app.route('/recieve_video', methods=['POST'])
def revieve_video():
    
    files = request.files

    if 'video' not in files:
        return jsonify({"error": "No video file provided"}), 400
    
    video_file = request.files['video']
    video_path = os.path.join('./uploads', video_file.filename)
    video_file.save(video_path)

    upload_path = os.path.join('./uploads', f"processed-{video_file.filename}")

    output = processingVideo(video_path,upload_path)

    if not output:
        os.remove(video_path)
        os.remove(upload_path)
        return jsonify({'message':'an error occured'}), 500

    try:

        if not os.path.exists('./uploads/most_suspicious_frame.jpg'):
            return jsonify({'message':'no kidnapping found'}), 200

        response = cloudinary.uploader.upload('./uploads/most_suspicious_frame.jpg')
        
        os.remove(video_path)
        os.remove(upload_path)
        os.remove('./uploads/most_suspicious_frame.jpg')

        return jsonify(response), 200
    
    except Exception as e:

        os.remove(video_path)
        os.remove(upload_path)

        return jsonify({
            'message':'unable to handle request'
        }), 500



if __name__ == "__main__":

    cloudinary.config(
        cloud_name = os.environ['CLOUDINARY_CLOUD_NAME'],
        api_key = os.environ['CLOUDINARY_API_KEY'],
        api_secret = os.environ['CLOUDINARY_API_SECRET'],
    )

    app.run(debug=True)