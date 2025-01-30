import sys
from typing import Tuple
import mlflow
from urllib.parse import urlparse
import numpy as np
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from neuro_mf  import ModelFactory
from us_visa.exception import USvisaException
from us_visa.logger import logging
from us_visa.utils.main_utils import load_numpy_array_data, load_object, save_object
from us_visa.entity.config_entity import ModelTrainerConfig
from us_visa.entity.artifact_entity import DataTransformationArtifact, ModelTrainerArtifact, ClassificationMetricArtifactTestData
from us_visa.entity.estimator import USvisaModel

class ModelTrainer:
    def __init__(self, data_transformation_artifact: DataTransformationArtifact,model_trainer_config: ModelTrainerConfig):
        
        self.data_transformation_artifact = data_transformation_artifact
        self.model_trainer_config = model_trainer_config



    def eval_metrics(self,y_test, y_pred):
            accuracy = accuracy_score(y_test, y_pred) 
            f1 = f1_score(y_test, y_pred)  
            precision = precision_score(y_test, y_pred)  
            recall = recall_score(y_test, y_pred)
            return accuracy, f1, precision, recall

    def get_model_object_and_report(self, train: np.array, test: np.array) -> Tuple[object, object]:
        try:
            logging.info("Using neuro_mf to get best model object and report")

            logging.info("Add metrics in mlfow")

            mlflow.set_registry_uri("DAGSHUB_URL")
            tracking_url_type_store = urlparse(mlflow.get_tracking_uri()).scheme

            with mlflow.start_run():
            
                model_factory = ModelFactory(model_config_path=self.model_trainer_config.model_config_file_path)
                
                
                x_train, y_train, x_test, y_test = train[:, :-1], train[:, -1], test[:, :-1], test[:, -1]

                best_model_detail = model_factory.get_best_model(X=x_train,y=y_train,base_accuracy=self.model_trainer_config.expected_accuracy_score_train_data)
                model_obj = best_model_detail.best_model
                
                y_pred = model_obj.predict(x_test)

                (accuracy, f1, precision, recall) = self.eval_metrics(y_test, y_pred)
            
                mlflow.log_metric('accuracy', accuracy)
                mlflow.log_metric('f1', f1)
                mlflow.log_metric('precision', precision)
                mlflow.log_metric('recall', recall)

                if tracking_url_type_store != "file":

                    mlflow.sklearn.log_model(model_obj, "model", registered_model_name="best_model")
                else:
                    mlflow.sklearn.log_model(model_obj, "model")

                logging.info("End metrics in mlfow")

                test_data_metric_artifact = ClassificationMetricArtifactTestData(accuracy=accuracy, f1_score=f1, precision_score=precision, recall_score=recall)
            
                return best_model_detail, test_data_metric_artifact
        
        except Exception as e:
            raise USvisaException(e, sys) from e
        

    def initiate_model_trainer(self, ) -> ModelTrainerArtifact:
        logging.info("Entered initiate_model_trainer method of ModelTrainer class")
        try:
            train_arr = load_numpy_array_data(file_path=self.data_transformation_artifact.transformed_train_file_path)
            test_arr = load_numpy_array_data(file_path=self.data_transformation_artifact.transformed_test_file_path)
            
            best_model_detail ,test_data_metric_artifact = self.get_model_object_and_report(train=train_arr, test=test_arr)
            
            preprocessing_obj = load_object(file_path=self.data_transformation_artifact.transformed_object_file_path)


            if best_model_detail.best_score < self.model_trainer_config.expected_accuracy_score_train_data:
                logging.info("No best model found with score more than base score")
                raise Exception("No best model found with score more than base score")

            usvisa_model = USvisaModel(preprocessing_object=preprocessing_obj,trained_model_object=best_model_detail.best_model)
            logging.info("Created usvisa model object with preprocessor and model")
            logging.info("Created best model file path.")
            save_object(self.model_trainer_config.trained_model_file_path, usvisa_model)

            model_trainer_artifact = ModelTrainerArtifact(trained_model_file_path=self.model_trainer_config.trained_model_file_path,test_data_metric_artifact=test_data_metric_artifact)
            logging.info(f"Model trainer artifact on test data: {model_trainer_artifact}")
            return model_trainer_artifact
        except Exception as e:
            raise USvisaException(e, sys) from e