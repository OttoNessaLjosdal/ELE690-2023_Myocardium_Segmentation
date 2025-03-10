import sys, os
sys.path.append('CardioMiner')
import numpy as np
from CropHeart import crop_heart
import pickle as p 
import orgim_scr as oi
import matplotlib.pyplot as plt 
import numpy as np 
import pydicom as dicom 
import time
from sklearn.model_selection import train_test_split



def nest_flatten(nested_list: list[list]) -> list:
    """ 
    nested list: a list of lists [[x],[y], ..., [a]]
    returns a flattened list [x, y, ..., a]
    """
    return [element for sublist in nested_list for element in sublist]

dataset = 'haglag'
delineation_location = {'haglag':'konsensus_leik_stein', 'vxvy':'erlend'}

filepath = '/home/prosjekt5/EKG/data/wmri/'
filepathDel = f'/home/prosjekt5/EKG/data/wmri/{delineation_location.get(dataset)}/'

prm = oi.userGetOrg(dataset) # Sets the user settings for the organization function within 0i.main()
prm['filepath'] = filepath # filepath must be changed to match the path to data.
prm['filepathDel'] = filepathDel 

print(prm.keys())
patients_with_delineation = [var for var in prm['Ptsgm'] if var] # Make a list of all the patients that have a deliniation
#print(List)
ids = []    # patient ID
imgs = []   # images
Mmyo = []   # Mask of myocardium
with open('log.txt', mode='w', encoding='utf-8') as log:
    start = time.perf_counter()
    print('starting')
    for i, patient in enumerate(patients_with_delineation):
        #print(f'#{i}, patient id: {patient}')
        try: 
            inD, b, prm_h, Pt_h = oi.main(dataset, patient) # Extract the info into inD. It contains pictures, delineations etc. 
        except Exception as e:
            log.write(f'#{i}: {patient}, oi.main(), {repr(e)}\n')
            print(f'failed at #{i} oi.main()')
            continue
        #print(inD.keys())
        try:
            cpD = crop_heart(inD, plot=0) # Crops the image of the heart to zoom more onto the myocard
        except Exception as e:
            log.write(f'{i}, {patient}, crop_heart(), {repr(e)}\n')
            print(f'failed at #{i} crop_heart()')
            continue
        cpD['id'] = patient
        ids.append(cpD['id'])
        imgs.append(cpD['X'])
        Mmyo.append(cpD['Mmyo'])
finish = time.perf_counter()
print(f'time: {(finish-start)//60} min, {round(((finish-start)/60-(finish-start)//60)*60, 2)} s')
imgs = np.asarray(imgs, dtype=object)
Mmyo = np.asarray(Mmyo, dtype=object)


# Write dataset presplit to file
with open(f"{dataset}_presplit.p", 'wb') as f:
    fdata = dict(
        images = imgs,
        masks = Mmyo,
        ids = ids,
    )
    p.dump(fdata, f, protocol=p.HIGHEST_PROTOCOL)


# Split dataset into training, validation and test sets
train_imgs, test_imgs, train_Mmyo, test_Mmyo, train_id, test_id = train_test_split(imgs, Mmyo, ids, test_size=0.25, train_size=0.75,random_state=1)
train_imgs, val_imgs, train_Mmyo, val_Mmyo, train_id, val_id = train_test_split(train_imgs, train_Mmyo, train_id, test_size=0.2, train_size=0.80, random_state=1)


# Create a separate test set file where the patient images are kept grouped.
# This is used to visualy evaluate the models in 'model_training_and_eval.py'.pred_patient_set by
# predicting on a whole image series of a single patient.
with open(f"{dataset}_test_patients_0_15_grouped.p", 'wb') as f:
    test_patients = dict()
    for i, test_patient in enumerate(test_id):
        test_patients[test_patient] = [
            test_imgs[i],
            test_Mmyo[i],
        ]
    p.dump(test_patients, f, protocol=p.HIGHEST_PROTOCOL)


# Create the main training, val and test set file. 
# Could potentially use a rework because of the move to ImageDataGenerator from
# tensorflow.keras.preprocessing.image
with open(f'{dataset}_imgs_and_Mmyo_0_15_validation.p', 'wb') as data_file:
    train_imgs = np.asarray(nest_flatten(train_imgs))
    train_Mmyo = np.asarray(nest_flatten(train_Mmyo))

    test_imgs = np.asarray(nest_flatten(test_imgs))
    test_Mmyo = np.asarray(nest_flatten(test_Mmyo))

    val_imgs = np.asarray(nest_flatten(val_imgs))
    val_Mmyo = np.asarray(nest_flatten(val_Mmyo))

    id_dict = {'full':ids, 'train':train_id, 'test':test_id, 'val':val_id}
    data_dict = {'train images':train_imgs,'train Mmyo':train_Mmyo, 'test images':test_imgs, 'test Mmyo':test_Mmyo, 'validation images':val_imgs, 'validation Mmyo':val_Mmyo, 'id':id_dict}

    p.dump(data_dict, data_file, protocol=p.HIGHEST_PROTOCOL)
