__author__ = 'adamfroimovitch'
from numpy import *
from PIL import Image
from PIL import ImageChops
import os

# Stack images using steepest descent method
# Private methods
def __totalSum(arr1):
    return sum(arr1)/arr1.size;

def __transform(a,b,c,d,e,f):
    #c: left-right
    #f: up-down
    return  (a, b, c, d, e, f);

def __clipPixel(pixel,threshold):
    if pixel < threshold:
        pixel = 0;
    return pixel;

def __threshold(im,threshold):
    imData = asarray(im).astype('int32');
    imData = [__clipPixel(pixel,threshold) for row in imData.tolist() for pixel in row]
    imt = Image.new("L",im.size);
    imt.putdata(imData);
    return imt;

def __crop(x,y,w,h,im):
    im = im.crop((x,y,w,h));
    return im;

def __translate(c,f,im):
    T = __transform(1,0,c,0,1,f);
    im = im.transform(im.size, Image.AFFINE,T);
    return im;

def __transformImage(c,f,im,shouldTranslate):
    if (shouldTranslate):
        im = __translate(c,f,im);
    x=y=0;
    w=im.size[0];
    h=im.size[1];

    if c < 0:
        x = -c
    elif c > 0:
        w -= c;

    if f < 0:
        y = -f
    elif f > 0:
        h -= f;

    im = __crop(x,y,w,h,im);

    return im;

def __dPhibyDcDf(im2,im1,c,f):

    im2_cp = __transformImage(c+1,f,im2,True);
    im2_cm = __transformImage(c-1,f,im2,True);
    im2_fp = __transformImage(c,f+1,im2,True);
    im2_fm = __transformImage(c,f-1,im2,True);

    im1_cp = __transformImage(c+1,f,im1,False);
    im1_cm = __transformImage(c-1,f,im1,False);
    im1_fp = __transformImage(c,f+1,im1,False);
    im1_fm = __transformImage(c,f-1,im1,False);

    # df by dc
    phi0 = __totalSum(asarray(ImageChops.subtract(im2_cp,im1_cp)).astype('int32'));
    phi1 = __totalSum(asarray(ImageChops.subtract(im2_cm,im1_cm)).astype('int32'));
    dfdc = (float(phi0)-float(phi1))/2;

    # df by df
    phi0 = __totalSum(asarray(ImageChops.subtract(im2_fp,im1_fp)).astype('int32'));
    phi1 = __totalSum(asarray(ImageChops.subtract(im2_fm,im1_fm)).astype('int32'));
    dfdf = (float(phi0)-float(phi1))/2;

    return (dfdc,dfdf);

# Public interface
# inputDir - Location of images
# stackedDir - Location to write stacked images for further processing if desired
# start - Index of first image to load. Should be of format <basename><index>.<bmp>
# basename - Basename for image names inside inputDir.  Should be of format <basename><index>.<bmp>
# readType - Image mode to read (RGB,L)
# writType - Image mode to write (RGB,L)

def stack(srcDir,files,stackedDir):

    c = 0 # left-right
    f = 0 # up-down
    start = 0;
    while True:
        try:
            im1R = Image.open(srcDir+"/"+files[start]).convert("RGB");
            im1L = __threshold(Image.open(srcDir+"/"+files[start]).convert("L"),40);
            imOutRData = asarray(im1R).astype('int32');
            imOutLData = asarray(im1L).astype('int32');
            break;
        except:
            print("File " + files[start] + "was not an image file");
            start += 1;

    files = files[start:];

    count = 2;
    for file in files:
        try:
            im2R =Image.open(srcDir+"/"+file).convert("RGB");
            im2L = __threshold(Image.open(srcDir+"/"+file).convert("L"),40);
        except:
            print("File " + files[start] + "was not an image file");
            continue;

        im2Lcrp = __transformImage(c,f,im2L,True);
        im1Lcrp = __transformImage(c,f,im1L,False);

        reps = 0
        phi = __totalSum(asarray(ImageChops.subtract(im2Lcrp,im1Lcrp)).astype('int32'));

        while (True):

            print("phi = " + str(phi) + "for c,f = " + str((c,f)));

            if (reps > 10 or phi < 0.05):
                break;

            dPhi = __dPhibyDcDf(im2L,im1L,c,f);
            dfdc = dPhi[0];
            dfdf = dPhi[1];

            ctemp = c;
            ftemp = f;
            alpha = 1000;
            innerPhi = phi;

            while (True):

                ctemp -= alpha*dfdc;
                ftemp -= alpha*dfdf;
                im2L_temp = __transformImage(ctemp,ftemp,im2L,True)
                im1L_temp = __transformImage(ctemp,ftemp,im1L,False)

                phi = __totalSum(asarray(ImageChops.subtract(im2L_temp,im1L_temp)).astype('int32'));

                if (phi <= innerPhi):
                    c = ctemp;
                    f = ftemp;
                    break;
                else:
                    ctemp = c;
                    ftemp = f;
                    alpha = alpha/3;


            reps += 1;

        im2TR = __translate(c,f,im2R);
        im2TR.save(stackedDir+"/"+str(count-2)+ ".tif",0);
        im2RData = asarray(im2TR).astype('int32');
        imOutRData = imOutRData + im2RData;

        im2TL = __translate(c,f,im2L);
        im2LData = asarray(im2TL).astype('int32');
        imOutLData = imOutLData + im2LData;
        im1L.putdata([int32(item/count) for row in imOutLData.tolist() for item in row])

        print("Saving " + stackedDir+"/"+str(count-2)+ ".tif");
        count += 1;

    iout32 = Image.new("RGB",im1R.size)
    data = [tuple(int32(pix/(count)) for pix in item) for row in imOutRData.tolist() for item in row]
    iout32.putdata(data)
    iout32.show()
    iout32.save("outStacked.tif",0);

# Filter images in stacked directory by standard deviation and average pixel value
# Private Methods
def __pixelParams(pixelTimeData):
    stDev = std(pixelTimeData)
    average = mean(pixelTimeData);
    return (average,stDev);

def __filterPixel(pixel,ave,stDev):
    value = 0;
    delta = abs(pixel - ave)
    if delta <= 1*stDev:
        value = pixel;
    return value;

def __filterChannel(channel,params):
    channelData = list();
    pixel = 0;
    for pixelTimeData in channel:
        print("Evaluating pixel # " + str(pixel))
        stDev = params[pixel][1];
        ave = params[pixel][0];
        values = [__filterPixel(pixel,ave,stDev) for pixel in pixelTimeData];
        value = sum(values);
        count = count_nonzero(array(values));
        pixel += 1;
        channelData.append(int32(value/count));
    return channelData

def __stackedData(stackedDir,files,readType):
    size = None;
    dataToProcess = list();
    for file in files:
        try:
            im = Image.open(stackedDir+"/"+file).convert(readType);
            imData = asarray(im).astype('int32');
            imFlat = [item for row in imData.tolist() for item in row]
            dataToProcess.append(imFlat);
            size = im.size;
        except:
            print("File " + file + "was not an image file");
    return [dataToProcess,size];

# Public interface
# stackedDir - Location of stacked images
# readType - Image mode to read. Supported modes = 'RBG','L'
# writeType - Image mode to write output.  Supported modes = 'RBG','L'
def filterStackedImages(stackedDir,readType,writeType):
    print("Begin stacking")
    files = [f for f in os.listdir(stackedDir)];
    stacked = __stackedData(stackedDir,files,readType)
    print("Files stacked")
    dataToProcess = stacked[0];
    originalSize = stacked[1];
    transformedData = array(dataToProcess).transpose();

    paramsMap = dict();
    channelID = 0;
    print("Begin variation calcs")
    for channel in transformedData:
        pixelVariation = list();
        paramsMap[channelID]=pixelVariation;
        for pixelTimeData in channel:
            pixelVariation.append(__pixelParams(pixelTimeData));
        channelID +=1;

    outputData = list();
    channelID = 0;

    print("Begin filtering")
    for channel in transformedData:
         pixelVariation = paramsMap[channelID];
         channelData = __filterChannel(channel,pixelVariation);
         outputData.append(channelData);
         channelID += 1;


    outputData = [tuple(item) for item in array(outputData).transpose().tolist()]

    iout32 = Image.new(writeType,originalSize)
    iout32.putdata(outputData);
    iout32.save("StackedFiltered"+writeType+".tif",0);


# Main program
srcDir = "j2-2x";
files = [f for f in os.listdir(srcDir)];
files = files[:50];

stack(srcDir,files,"Data")
filterStackedImages('Data','RGB','RGB')








