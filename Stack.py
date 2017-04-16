__author__ = 'adamfroimovitch'
from numpy import *
from PIL import Image
from PIL import ImageChops

import os
#  $ ffmpeg -i video0006.avi assets/image%d.bmp




def imDiff(arr1,arr2):
    diff = abs(array(arr1)-array(arr2));
    return diff

def imSum(arr1,arr2,norm):
    addition = (arr1+arr2)
    if norm:
        addition = addition/2;

    return addition

def totalSum(arr1):
    return sum(arr1)/arr1.size;

def transform(a,b,c,d,e,f):
    return  (a, b, c, d, e, f);

def crop(x,y,w,h,im):
    im = im.crop((x,y,w,h));
    return im;

def translate(c,f,im):
    T = transform(1,0,c,0,1,f);
    im = im.transform(im.size, Image.AFFINE,T);
    return im;

def transformImage(c,f,im,shouldTranslate):

    if (shouldTranslate):
        im = translate(c,f,im);

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

    im = crop(x,y,w,h,im);

    return im;


def stack(inputDir,stackedDir,start,basename,stackedBaseName,readType,writeType):

    path = inputDir+"/"+basename;
    a = 1
    b = 0
    c = 0 # left-right
    d = 0
    e = 1
    f = 0 # up-down

    index = start;
    im1 = Image.open(path+"0"+str(index)+".bmp").convert(readType);
    im1Data = asarray(im1).astype('int32');
    im1OutData = asarray(im1).astype('int32');

    while (index < start + 50):

        index = index + 1;
        name = path+"0"+str(index)+".bmp"
        im2 =Image.open(name).convert(readType);
        im2crp = transformImage(c,f,im2,True);

        reps = 0
        phi = totalSum(asarray(ImageChops.subtract(im2crp,transformImage(c,f,im1,False))).astype('int32'));

        while (True):

            if (reps > 10 or phi < 0.1):
                break;

            im2_cp = transformImage(c+1,f,im2,True);
            im2_cm = transformImage(c-1,f,im2,True);
            im2_fp = transformImage(c,f+1,im2,True);
            im2_fm = transformImage(c,f-1,im2,True);

            im1_cp = transformImage(c+1,f,im1,False);
            im1_cm = transformImage(c-1,f,im1,False);
            im1_fp = transformImage(c,f+1,im1,False);
            im1_fm = transformImage(c,f-1,im1,False);

            # df by dc
            phi0 = totalSum(asarray(ImageChops.subtract(im2_cp,im1_cp)).astype('int32'));
            phi1 = totalSum(asarray(ImageChops.subtract(im2_cm,im1_cm)).astype('int32'));
            dfdc = (float(phi0)-float(phi1))/2;

            # df by df
            phi0 = totalSum(asarray(ImageChops.subtract(im2_fp,im1_fp)).astype('int32'));
            phi1 = totalSum(asarray(ImageChops.subtract(im2_fm,im1_fm)).astype('int32'));
            dfdf = (float(phi0)-float(phi1))/2;

            ctemp = c;
            ftemp = f;
            alpha = 300;
            innerPhi = phi;
            while (True):

                ctemp -= alpha*dfdc;
                ftemp -= alpha*dfdf;

                im2_temp = transformImage(ctemp,ftemp,im2,True)
                im1_temp = transformImage(ctemp,ftemp,im1,False)

                phi = totalSum(asarray(ImageChops.subtract(im2_temp,im1_temp)).astype('int32'));

                if (phi <= innerPhi):
                    c = ctemp;
                    f = ftemp;
                    break;
                else:
                     ctemp = c;
                     ftemp = f;
                     alpha = alpha/3;


            reps += 1;

        im2T = translate(c,f,im2);
        im2Data = asarray(im2T).astype('int32');
        im1OutData = im1OutData + im2Data;

        data = None;
        if (readType == 'RGB'):
             data = [tuple(item) for row in im2Data.tolist() for item in row]
        else:
            data = [item for row in im2Data.tolist() for item in row]

        iout32 = Image.new(writeType,im1.size)
        iout32.putdata(data)
        iout32.save(stackedDir+"/"+stackedBaseName+str(index)+ ".tiff",0);
        print("Saving " + name);

    iout32 = Image.new(writeType,im1.size)

    data = None;
    if (readType == 'RGB'):
        data = [tuple(int32(pix/(index-start)) for pix in item) for row in im1OutData.tolist() for item in row]
    else:
        data = [item for row in im1OutData.tolist() for item in row]

    iout32.putdata(data)

    iout32.show()
    iout32.save("outStacked"+str(writeType)+".tiff",0);


def pixelParameters(channel,params):
    for pixeldata in channel:
        stdev = std(pixeldata)
        average = mean(pixeldata);
        params.append((average,stdev));
    return params;

def filterStackedImages(stackedDir,readType,writeType):

     im = None;
     dataToProcess = list();
     files = [f for f in os.listdir(stackedDir)];
     for file in files:
        file_name,extension = os.path.splitext(file);
        if extension == ".tiff":

            im = Image.open(stackedDir+"/"+file).convert(readType);
            imData = asarray(im).astype('int32');
            imFlat = [item for row in imData.tolist() for item in row]
            dataToProcess.append(imFlat);

     transformedData = array(dataToProcess).transpose();

     paramsMap = dict();
     channelID = 0;
     for channel in transformedData:
        params = list();
        paramsMap[channelID]=params;
        for pixeldata in channel:
            stdev = std(pixeldata)
            average = mean(pixeldata);
            params.append((average,stdev));
        channelID +=1;

     outputData = list();
     channelID = 0;
     for channel in transformedData:
         channelData = list();
         params = paramsMap[channelID];
         pixel = 0;
         for pixeldata in channel:
             print("Evaluating pixel # " + str(pixel))
             value = 0;
             stdev = params[pixel][1];
             ave = params[pixel][0];
             count = 1;
             image = 0;
             for individualPixelData in pixeldata:
                 delta = abs(individualPixelData - ave)
                 if delta <= 0.5*stdev:
                     value += individualPixelData;
                     count += 1;
                 image += 1;
             pixel += 1;
             channelData.append(int32(value/count));
         outputData.append(channelData);
         channelID += 1;


     outputData = [tuple(item) for item in array(outputData).transpose().tolist()]

     iout32 = Image.new(writeType,im.size)
     iout32.putdata(outputData);
     iout32.save("outStackedFiltered32.tiff",0);


#stack("j2","Data",554,"image","image",'RGB','RGB')
filterStackedImages('Data','RGB','RGB')














# def filterStackedImages(stackedDir,readType):
#
#      im = None;
#      dataToProcess = list();
#      files = [f for f in os.listdir(stackedDir)];
#      for file in files:
#         file_name,extension = os.path.splitext(file);
#         if extension == ".tiff":
#
#             imGrey = Image.open(stackedDir+"/"+file).convert(readType);
#             imData = asarray(imGrey).astype('int32');
#             imFlat = [item for row in imData.tolist() for item in row]
#             dataToProcess.append(imFlat);
#
#      # transformedData will contain a flat list of pixels for each channel
#      # r = 0, g = 1 and b = 2, same as if its grey scale
#      transformedData = array(dataToProcess).transpose();
#
#      params = list();
#      for pixeldata in transformedData:
#         stdev = std(pixeldata)
#         average = mean(pixeldata);
#         params.append((average,stdev));
#
#
#      outputData = list();
#      pixel = 0;
#      for pixeldata in transformedData:
#          print("Evaluating pixel # " + str(pixel))
#          value = 0;
#          stdev = params[pixel][1];
#          ave = params[pixel][0];
#          count = 1;
#          image = 0;
#          imageList = list();
#          for individualPixelData in pixeldata:
#              delta = abs(individualPixelData - ave)
#              if delta < 1*stdev:
#                  value += individualPixelData;
#                  count += 1;
#              image += 1;
#          pixel += 1;
#          outputData.append(value/count);
#
#      iout32 = Image.new("I",im.size)
#      iout32.putdata(outputData);
#      iout32.save("outStackedFiltered32.tiff",0);










