from pyspark import SparkContext, SparkConf
from pyspark.ml.classification import LogisticRegression
from pyspark.ml.regression import LinearRegression
from pyspark.sql import SQLContext, Row
from pyspark.sql.types import IntegerType
from pyspark.sql.functions import UserDefinedFunction
from pyspark.ml.linalg import Vectors

import os
import pyspark_csv as pycsv

os.environ["SPARK_LOCAL_IP"] = "127.0.0.1" # set local IP

DATADIR = "./Desktop/BDP/predict3/AQI2/data"
 # data directory

def mySparkContext():
    """
    Sets the Spark Context
    """
    conf = (SparkConf()
            .setMaster("local")
            .setAppName("predictAQI")
            .set("spark.executor.memory", "4g"))
    sc = SparkContext(conf = conf)
    return sc

sc = mySparkContext()
sqlCtx = SQLContext(sc)
sc.addPyFile("Desktop/BDP/predict3/AQI2/pyspark_csv.py")

def loadDF(filename):
    """
    Load and parse filename as pyspark.sql.DataFrame
    using pyspark_csv.py
    """
    path = os.path.join(DATADIR, filename)
    plain = sc.textFile(path)
    df = pycsv.csvToDataFrame(sqlCtx, plain, sep=',')
    return df

# DataFrames are immutable. Must transform RDD to another RDD for binary sex


#------------------------------------------------------------

if __name__ == "__main__":

    train = loadDF("train.csv")
    test = loadDF("aqi.csv")

    testNumber = test.select('Number').rdd.map(lambda x: x.Number)

    train = train.select('AQI', 'Temp Arithmetic Mean', 'Wind SpeedArithmetic Mean',
    'Wind Direction Arithmetic Mean', 'Barometric pressure Arithmetic Mean', 'CO Arithmetic Mean',
    'SO2 Arithmetic Mean', 'NO2 Arithmetic Mean', 'Ozone Arithmetic Mean', 'PM25 Mean')

    test = test.select('Temp Arithmetic Mean', 'Wind SpeedArithmetic Mean',
    'Wind Direction Arithmetic Mean', 'Barometric pressure Arithmetic Mean', 'CO Arithmetic Mean',
    'SO2 Arithmetic Mean', 'NO2 Arithmetic Mean', 'Ozone Arithmetic Mean', 'PM25 Mean')



    # format train for Linear Regression as (label, features)
    ntrain = train.rdd.map(lambda x: Row(label = float(x[0]) \
         ,features = Vectors.dense(x[1:]))).toDF().cache() # Linear Regression is iterative, need caching
    ntest = test.rdd.map(lambda x: Row(features = Vectors.dense(x[0:]))).toDF()

    lr = LinearRegression(maxIter = 100, regParam = 0.4, elasticNetParam=0.7)
    model = lr.fit(ntrain)

    print("Coefficients: " + str(model.coefficients))
    print("Intercept: " + str(model.intercept))

    pred = model.transform(ntest).select('prediction').rdd.map(lambda x: x.prediction)

    # configure the submission format as follows
    submit = sqlCtx.createDataFrame(testNumber.zip(pred), ["Number", "AQI"])
    """
    NOTE: rdd1.zip(rdd2) works provided that both RDDs have the same partitioner and the same number
    of elements per partition, otherwise should either repartition or can do:

    """
    os.chdir(DATADIR)
    # file is small so can save pandas.DataFrame as csv
    submit.toPandas().to_csv("prediction.csv", index = False)
    # if not, should saveAsTextFile:
    # submit.rdd.saveAsTextFile("/BDP/data/prediction")
    sc.stop()
