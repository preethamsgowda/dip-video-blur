from tqdm import tqdm
import os
import errno
import cv2
import requests
import threading
import shutil

url = 'YOUR_AWS_LAMBDA_URL_HERE'

def createDirectory(directoryPath):
    # Create folder if it doesnt exist
    if not os.path.exists(directoryPath):
        try:
            os.makedirs(directoryPath)
        except OSError as exc: # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise

def deleteDirectory(directoryPath):
    shutil.rmtree(directoryPath)

def extractFrames(vCapture, tempDir, pbarExtractingFrames):
    success,image = vCapture.read()
    count = 1
    while success:
        cv2.imwrite(tempDir+"/oframe_%d.jpg" % count, image) # save frame as JPEG file      
        success,image = vCapture.read()
        pbarExtractingFrames.update(1)
        count += 1
    pbarExtractingFrames.close()

def blurFrame(frame, tempDir, pbarProcessing, params):
    with open(tempDir+"/oframe_"+str(frame)+".jpg" , "rb") as image_file:
        image = image_file.read()
    headers = {"Content-Type":"multipart/form-data", "Authorization":"None"}
    response = requests.post(url, data=image, headers=headers, params = params)
    with open(tempDir+"/pframe_"+str(frame)+".jpg", "wb") as out:
        out.write(response.content)
        out.flush()
        pbarProcessing.update(1)

def main(videoPath, dimensions, startTime, endTime):
    """
    This is the main entry point for the program
    """

    # Temp directory path
    tempDir = './temp'

    # Read original video
    oVid = cv2.VideoCapture(videoPath)

    # Fetch original video dimensions
    oWidth  = int(oVid.get(cv2.CAP_PROP_FRAME_WIDTH)) # original width
    oHeight = int(oVid.get(cv2.CAP_PROP_FRAME_HEIGHT)) # original height

    # Get blur segment dimenstions
    topLeftX, topLeftY, sWidth, sHeight = dimensions # segmentWidth, segmentHeight

    ## Preliminary Checks #1
    # Check if blur segment dimensions are within bounds
    if(topLeftX < 0) or (topLeftX > oHeight):
        raise ValueError('Invalid topLeftX dimensions!')
    if(topLeftY < 0) or (topLeftY > oWidth):
        raise ValueError('Invalid topLeftY dimensions!')
    if(oHeight < 0) or ((topLeftX+sHeight) > oHeight):
        raise ValueError('Invalid heightOut dimensions!')
    if(oWidth < 0) or ((topLeftY+sWidth) > oWidth):
        raise ValueError('Invalid widthOut dimensions!')

    # Get original video frame rate
    frameRate = int(oVid.get(cv2.CAP_PROP_FPS))
    
    # Total frames in video
    totalFrames = int(oVid.get(cv2.CAP_PROP_FRAME_COUNT))

    # Extract hour, minute and seconds from start and end time
    sHour, sMinute, sSecond = startTime.split(':')
    eHour, eMinute, eSecond = endTime.split(':')
    sHour, sMinute, sSecond = int(sHour), int(sMinute), int(sSecond)
    eHour, eMinute, eSecond = int(eHour), int(eMinute), int(eSecond)

    print('start: ', sHour, sMinute, sSecond)
    print('end: ', eHour, eMinute, eSecond)

    # Get task start frame and end frame
    startFrame = (((sHour*60*60 + sMinute*60 + sSecond) - 1) * frameRate) + 1
    endFrame = (eHour*60*60 + eMinute*60 + eSecond) * frameRate

    ## Preliminary Checks #2
    # Check if start frame is less than 1
    if startFrame < 1:
        startFrame = 1
    # Check if end frame is greater than total frames
    if endFrame > totalFrames:
        if (endFrame - totalFrames) < frameRate:
            endFrame = totalFrames
        else:
            raise ValueError('End frame number exceeds total frames number!')
    
    # Check if end time is less than start time
    if startFrame > endFrame:
        raise ValueError('End frame number is greater than start frame number!')

    # Generate list of frames
    frames = [*range(startFrame, endFrame+1)]

    # Progress bar to track frame extraction
    pbarProcessingFrames = tqdm(total=totalFrames)
    pbarProcessingFrames.set_description("Extracting Frames ")

    # Create temporary directory
    print("  Creating temp directory")
    createDirectory(tempDir)

    # Extract frames to temp directory
    extractFrames(oVid, tempDir, pbarProcessingFrames) # -- Uncomment this

    # Progress bar to track frame processing
    pbarProcessingFrames = tqdm(total=len(frames))
    pbarProcessingFrames.set_description("Processing Frames ")
    
    ## Params for the request
    # gs: gradiant stride
    # mgi: 
    # in: intensity
    # sx: segment start x
    # sy: segment start y
    # sh: segment height
    # sw: segment width
    params = {'gs': 5, 'mgi': 10, 'in': 11, 'sx': topLeftX, 'sy': topLeftY, 'sh': sHeight, 'sw': sWidth}

    threads = []
    # Put some work in the queue
    for frame in frames:
        t = threading.Thread(target=blurFrame, args=[frame, tempDir, pbarProcessingFrames, params])
        t.start()
        threads.append(t)
    
    for thread in threads:
        thread.join()

    # # Progress bar to track loading Image Array
    # pbarLoadingImageArray = tqdm(total=totalFrames)
    # pbarLoadingImageArray.set_description("Loading processed image array ")

    fileList = []
    for frame in range(1, totalFrames+1):
        # Check if frame is processed
        if frame in frames:
            fileName = "pframe_%d.jpg" % frame
        else:
            fileName = "oframe_%d.jpg" % frame
        filePath = tempDir+'/'+fileName
        fileList.append(filePath)
    
    video_name = 'output.avi'
    video = cv2.VideoWriter(video_name, cv2.VideoWriter_fourcc(*'DIVX'), 25, (oWidth, oHeight))

    for frame in fileList:
        video.write(cv2.imread(frame))

    cv2.destroyAllWindows()

    # Create temporary directory
    print("  Deleting temp directory")
    deleteDirectory(tempDir)

if __name__ == "__main__":
    main('bufallo.mp4', (100, 390, 100, 100), '00:00:10', '00:00:20')
