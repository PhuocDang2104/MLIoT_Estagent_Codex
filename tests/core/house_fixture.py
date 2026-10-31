"""Hand-authored synthetic plan. Not inferred from the test color images."""
def house_plan(asset_ids=('image1','image2')):
    return {'status':'provisional','scale':'assumed','scale_evidence':'',
        'summary':'Synthetic kitchen and empty living room; geometry for automated QA only.',
        'questions':[],'assumptions':['All dimensions and camera poses are synthetic estimates.'],
        'spaces':[
            {'id':'r01','label':'Kitchen fixture','polygon':[{'x':0,'z':0},{'x':4,'z':0},{'x':4,'z':4},{'x':0,'z':4}],
             'height':2.7,'floor_material':'tile','wall_material':'plaster','sources':[asset_ids[0]],
             'openings':[{'wall':1,'offset':1.4,'width':1.2,'bottom':0,'height':2.1,'kind':'passage','sources':[asset_ids[0]]},
                         {'wall':0,'offset':1,'width':2,'bottom':1.2,'height':1.1,'kind':'window','sources':[asset_ids[0]]}]},
            {'id':'r02','label':'Living fixture','polygon':[{'x':4,'z':0},{'x':8,'z':0},{'x':8,'z':4},{'x':4,'z':4}],
             'height':2.7,'floor_material':'wood','wall_material':'plaster','sources':[asset_ids[1]],
             'openings':[{'wall':3,'offset':1.4,'width':1.2,'bottom':0,'height':2.1,'kind':'passage','sources':[asset_ids[1]]}]}],
        'captures':[{'checkpoint_id':f'cp{i+1:02}','room_id':f'r{i+1:02}',
                     'position':{'x':2+i*4,'y':1.6,'z':2},'heading':0,'accuracy':'approximate'} for i in range(2)],
        'fixtures':[{'room_id':'r01','kind':kind,'position':{'x':x,'y':y,'z':.55},
            'width':width,'depth':.6,'height':height,'rotation':0,'material':'wood',
            'sources':[asset_ids[0]],'evidence':'Synthetic fixture evidence, not a real photo.'}
            for kind,x,y,width,height in [('cabinet',.7,0,.8,.9),('sink',1.6,0,1,.9),('stove',2.6,0,.8,.9),('upper_cabinet',.7,1.6,.8,.7),('fridge',3.4,0,.6,1.8)]]}
