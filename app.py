from ultralytics import YOLO
from flask import Flask, jsonify, request
import os
import uuid
from flask_cors import CORS
import cv2
import cloudinary
import cloudinary.uploader
from cloudinary import CloudinaryImage
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
            os.remove(video_path)
            os.remove(upload_path)
            return jsonify({
                'message':'no kidnapping found',
                'status':False
            }), 200

        image_response = cloudinary.uploader.upload('./uploads/most_suspicious_frame.jpg')
        public_id = image_response.get('public_id')

        response = CloudinaryImage(public_id).build_url(
            height=200, width=250
        )

        os.remove(video_path)
        os.remove(upload_path)
        os.remove('./uploads/most_suspicious_frame.jpg')

        return jsonify({
            'image_link': response,
            'status': True
        }), 200
    
    except Exception as e:

        os.remove(video_path)
        os.remove(upload_path)

        return jsonify({
            'message':'unable to handle request'
        }), 500
    
@app.route('/recieve_image', methods=['POST'])
def revieve_image():

    try:

        files = request.files
        print('Request Form : ',request.form.get('title'))

        if 'image' not in files:
            return jsonify({'message':'no image input'}), 400
        
        image_file = request.files['image']
        unique_id = uuid.uuid4()
        image_path = os.path.join('./uploads', f'{unique_id}-{image_file.filename}')
        image_file.save(image_path)

        model = YOLO('best.pt')
        result = model.predict(image_path)

        annotated_frame = result[0].plot()
        r = result[0]

        for box in r.boxes:

            cls_id = int(box.cls)
            conf = round(float(box.conf) * 100, 1)

            if r.names[cls_id] == 'Kidnap' and round(float(box.conf) * 100, 1) > 70:

                print('exe')

                output_path = f'processed-{image_file.filename.replace(" ","-")}'
                cv2.imwrite(output_path,annotated_frame.copy())

                image_response = cloudinary.uploader.upload(output_path)
                public_id = image_response.get('public_id')

                response = CloudinaryImage(public_id).build_url(
                    height=200, width=250
                )

                os.remove(image_path)
                return jsonify({
                    'image_link': response,
                    'status': True
                }), 200

        os.remove(image_path)
        
        return jsonify(
            {
                'message':'no vulnerebility found',
                'status': False,
            }
        ), 200
    
    except Exception as e:

        return jsonify(
            {
                'message':'internal server error'
            }
        ), 500

if __name__ == "__main__":

    cloudinary.config(
        cloud_name = os.environ['CLOUDINARY_CLOUD_NAME'],
        api_key = os.environ['CLOUDINARY_API_KEY'],
        api_secret = os.environ['CLOUDINARY_API_SECRET'],
    )

    app.run(host='0.0.0.0', port='5000',debug=True)