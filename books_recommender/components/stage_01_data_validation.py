import os
import sys
import ast 
import pandas as pd
import pickle
from books_recommender.logger.log import logging
from books_recommender.config.configuration import AppConfiguration
from books_recommender.exception.exception_handler import AppException

class DataValidation:
    def __init__(self, app_config=AppConfiguration()):
        try:
            self.data_validation_config = app_config.get_data_validation_config()
        except Exception as e:
            raise AppException(e, sys) from e

    def _read_csv_with_compatibility(self, file_path):
        """Helper method to handle pandas version compatibility for read_csv"""
        read_params = {
            'filepath_or_buffer': file_path,
            'sep': ";",
            'encoding': 'latin-1',
            'low_memory': False  # To handle mixed types warning
        }
        
        # Handle pandas version compatibility
        if pd.__version__ >= '1.3.0':
            read_params['on_bad_lines'] = 'skip'
        else:
            read_params['error_bad_lines'] = False
            
        return pd.read_csv(**read_params)

    def preprocess_data(self):
        try:
            # Read data with version-compatible method
            ratings = self._read_csv_with_compatibility(
                self.data_validation_config.ratings_csv_file
            )
            books = self._read_csv_with_compatibility(
                self.data_validation_config.books_csv_file
            )
            
            logging.info(f"Shape of ratings data file: {ratings.shape}")
            logging.info(f"Shape of books data file: {books.shape}")

            # Process books data
            books = books[['ISBN', 'Book-Title', 'Book-Author', 
                         'Year-Of-Publication', 'Publisher', 'Image-URL-L']]
            
            books.rename(columns={
                "Book-Title": 'title',
                'Book-Author': 'author',
                "Year-Of-Publication": 'year',
                "Publisher": "publisher",
                "Image-URL-L": "image_url"
            }, inplace=True)

            # Process ratings data
            ratings.rename(columns={
                "User-ID": 'user_id',
                'Book-Rating': 'rating'  # Fixed typo from original (Book-Rating)
            }, inplace=True)

            # Filter active users
            active_users = ratings['user_id'].value_counts() > 200
            active_users = active_users[active_users].index
            ratings = ratings[ratings['user_id'].isin(active_users)]

            # Merge and filter data
            ratings_with_books = ratings.merge(books, on='ISBN')
            number_rating = ratings_with_books.groupby('title')['rating'].count().reset_index()
            number_rating.rename(columns={'rating': 'num_of_rating'}, inplace=True)
            final_rating = ratings_with_books.merge(number_rating, on='title')

            # Filter popular books
            final_rating = final_rating[final_rating['num_of_rating'] >= 50]
            final_rating.drop_duplicates(['user_id', 'title'], inplace=True)
            logging.info(f"Shape of the final clean dataset: {final_rating.shape}")
                        
            # Save cleaned data
            os.makedirs(self.data_validation_config.clean_data_dir, exist_ok=True)
            clean_data_path = os.path.join(
                self.data_validation_config.clean_data_dir,
                'clean_data.csv'
            )
            final_rating.to_csv(clean_data_path, index=False)
            logging.info(f"Saved cleaned data to {clean_data_path}")

            # Save serialized objects
            os.makedirs(self.data_validation_config.serialized_objects_dir, exist_ok=True)
            pickle_path = os.path.join(
                self.data_validation_config.serialized_objects_dir,
                "final_rating.pkl"
            )
            with open(pickle_path, 'wb') as f:
                pickle.dump(final_rating, f)
            logging.info(f"Saved final_rating serialization object to {pickle_path}")

        except Exception as e:
            raise AppException(e, sys) from e

    def initiate_data_validation(self):
        try:
            logging.info(f"{'='*20}Data Validation log started.{'='*20} ")
            self.preprocess_data()
            logging.info(f"{'='*20}Data Validation log completed.{'='*20} \n\n")
        except Exception as e:
            raise AppException(e, sys) from e