import json
import cv2
import base64

def write_to_file(save_path, data):
  with open(save_path, "wb") as f:
    f.write(base64.b64decode(data))

def lambda_handler(event, context):
    write_to_file("/tmp/photo.png", event["body"])
    # Read the image
    image = cv2.imread("/tmp/photo.png")
    
    gradiant_stride = int(event["multiValueQueryStringParameters"]["gs"][0])
    max_iterations = int(event["multiValueQueryStringParameters"]["mgi"][0])
    kernal_size = int(event["multiValueQueryStringParameters"]["in"][0])
    sx = int(event["multiValueQueryStringParameters"]["sx"][0])
    sy = int(event["multiValueQueryStringParameters"]["sy"][0])
    sw = int(event["multiValueQueryStringParameters"]["sw"][0])
    sh = int(event["multiValueQueryStringParameters"]["sh"][0])
    
    iteration = 0
    while True:
        change = (iteration*gradiant_stride)
        xStart = sx + change
        yStart = sy + change
        xEnd = (sx + sh) - change
        yEnd = (sy + sw) - change
        if (xStart >= xEnd) or (yStart >= yEnd) or iteration >= max_iterations:
            break
        image[xStart:xEnd, yStart:yEnd, :] = cv2.GaussianBlur(image[xStart:xEnd, yStart:yEnd, :], (kernal_size, kernal_size), 0)
        iteration +=1
    
    # Write image to /tmp
    cv2.imwrite("/tmp/our_image.png", image)
    
    # Convert image into utf-8 encoded base64
    with open("/tmp/our_image.png", "rb") as imageFile:
        str = base64.b64encode(imageFile.read())
        encoded_img = str.decode("utf-8")
    
    return {
      "isBase64Encoded": True,
      "statusCode": 200,
      "headers": { "content-type": "image/jpeg"},
      "body":  encoded_img
    }