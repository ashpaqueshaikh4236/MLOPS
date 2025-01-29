import sys
from us_visa.exception import USvisaException
from us_visa.logger import logging
from us_visa.components.data_ingestion import DataIngestion
from us_visa.components.data_validation import DataValidation
from us_visa.components.data_transformation import DataTransformation
from us_visa.components.model_trainer import ModelTrainer
from us_visa.components.model_evaluation import ModelEvaluation
from us_visa.components.model_pusher import ModelPusher


from us_visa.entity.config_entity import (DataIngestionConfig,
                                          DataValidationConfig,
                                          DataTransformationConfig,
                                          ModelTrainerConfig,
                                          ModelEvaluationConfig,
                                          ModelPusherConfig)

from us_visa.entity.artifact_entity import (DataIngestionArtifact,
                                            DataValidationArtifact,
                                            DataTransformationArtifact,
                                            ModelTrainerArtifact,
                                            ModelEvaluationArtifact,
                                            ModelPusherArtifact)



class TrainPipeline:
    def __init__(self):
        self.data_ingestion_config = DataIngestionConfig()
        self.data_validation_config = DataValidationConfig()
        self.data_transformation_config = DataTransformationConfig()
        self.model_trainer_config = ModelTrainerConfig()
        self.model_evaluation_config = ModelEvaluationConfig()
        self.model_pusher_config = ModelPusherConfig()


    def start_data_ingestion(self) -> DataIngestionArtifact:

        try:
            logging.info("<----------Entered the start_data_ingestion method of TrainPipeline class---------->")
            logging.info("Getting the data from mongodb")
            data_ingestion = DataIngestion(data_ingestion_config=self.data_ingestion_config)
            data_ingestion_artifact = data_ingestion.initiate_data_ingestion()
            logging.info("Got the train_set and test_set from mongodb")
            logging.info("----->Exited the start_data_ingestion method of TrainPipeline class<-----")
            return data_ingestion_artifact
        except Exception as e:
            raise USvisaException(e, sys) from e
        


    def start_data_validation(self, data_ingestion_artifact: DataIngestionArtifact) -> DataValidationArtifact:
        logging.info("<----------Entered the start_data_validation method of TrainPipeline class---------->")

        try:
            data_validation = DataValidation(data_ingestion_artifact=data_ingestion_artifact,data_validation_config=self.data_validation_config)
            data_validation_artifact, drift_status = data_validation.initiate_data_validation()
            logging.info("Performed the data validation operation")
            logging.info("----->Exited the start_data_validation method of TrainPipeline class<-----")
            return data_validation_artifact, drift_status

        except Exception as e:
            raise USvisaException(e, sys) from e



    def start_data_transformation(self, data_ingestion_artifact: DataIngestionArtifact, data_validation_artifact: DataValidationArtifact) -> DataTransformationArtifact:
        logging.info("<----------Entered the start_data_transformation method of TrainPipeline class---------->")
        try:
            data_transformation = DataTransformation(data_ingestion_artifact=data_ingestion_artifact,data_transformation_config=self.data_transformation_config,data_validation_artifact=data_validation_artifact)
            data_transformation_artifact = data_transformation.initiate_data_transformation()
            logging.info("----->Exited the start_data_transformation method of TrainPipeline class<-----")
            return data_transformation_artifact
        
        except Exception as e:
            raise USvisaException(e, sys)
        



    def start_model_trainer(self, data_transformation_artifact: DataTransformationArtifact) -> ModelTrainerArtifact:
        logging.info("<----------Entered the start_model_trainer method of TrainPipeline class---------->")
        try:
            model_trainer = ModelTrainer(data_transformation_artifact=data_transformation_artifact,model_trainer_config=self.model_trainer_config)
            model_trainer_artifact = model_trainer.initiate_model_trainer()
            logging.info("----->Exited the start_model_trainer method of TrainPipeline class<-----")
            return model_trainer_artifact

        except Exception as e:
            raise USvisaException(e, sys)
        

    def start_model_evaluation(self, data_ingestion_artifact: DataIngestionArtifact, model_trainer_artifact: ModelTrainerArtifact) -> ModelEvaluationArtifact:
        logging.info("<----------Entered the start_model_evaluation method of TrainPipeline class---------->")
        try:
            model_evaluation = ModelEvaluation(model_eval_config=self.model_evaluation_config, data_ingestion_artifact=data_ingestion_artifact,model_trainer_artifact=model_trainer_artifact)
            model_evaluation_artifact = model_evaluation.initiate_model_evaluation()
            logging.info("----->Exited the start_model_evaluation method of TrainPipeline class<-----")
            return model_evaluation_artifact
        
        except Exception as e:
            raise USvisaException(e, sys)
        


    def start_model_pusher(self, model_evaluation_artifact: ModelEvaluationArtifact) -> ModelPusherArtifact:
        logging.info("<----------Entered the start_model_pusher method of TrainPipeline class---------->")
        try:
            model_pusher = ModelPusher(model_evaluation_artifact=model_evaluation_artifact,model_pusher_config=self.model_pusher_config)
            model_pusher_artifact = model_pusher.initiate_model_pusher()
            logging.info("----->Exited the start_model_pusher method of TrainPipeline class<-----")
            return model_pusher_artifact
        
        except Exception as e:
            raise USvisaException(e, sys)


    def run_pipeline(self) -> None:
        try:
            data_ingestion_artifact = self.start_data_ingestion()
            data_validation_artifact, drift_status = self.start_data_validation(data_ingestion_artifact=data_ingestion_artifact)

            if drift_status == False:
                data_transformation_artifact = self.start_data_transformation(data_ingestion_artifact=data_ingestion_artifact, data_validation_artifact=data_validation_artifact)
                model_trainer_artifact = self.start_model_trainer(data_transformation_artifact=data_transformation_artifact)
                model_evaluation_artifact = self.start_model_evaluation(data_ingestion_artifact=data_ingestion_artifact, model_trainer_artifact=model_trainer_artifact)

                if not model_evaluation_artifact.is_model_accepted:
                    logging.info("Model not accepted. Skipping model pusher...............")
                else:
                    model_pusher_artifact = self.start_model_pusher(model_evaluation_artifact=model_evaluation_artifact)
            else:
                logging.info("Validation complete: No drift found, all pipeline steps skipped...............")

        except Exception as e:
            logging.error(f"An error occurred during pipeline execution: {str(e)}")
            raise e

        