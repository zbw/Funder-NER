import json
from nlu.prediction import predict

context = 'ralized linear model Acknowledgments We gratefully thank Ilka Schlitter and Laith Al-Sayegh for their support in collecting the patient level cost da'
prediction = predict(context)
print(json.dumps(prediction, indent=2))
