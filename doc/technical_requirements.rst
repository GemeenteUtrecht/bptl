.. _technical-requirements:


Software requirements
=====================
=======================  ==============
Software/framework       Version        
-----------------------  --------------
Python                   3.10
PostgreSQL               14+  
Node                     13
=======================  ==============

The current python dependencies can be found in github repo bptl/requirements/production.txt.
The current node dependencies can be found in github repo bptl/package.json.


Hardware requirements
=====================

Currently in our production implementation we have ~50 concurrent users and run the following
kubernetes settings:

=======================  ==============
Resource                 Values        
-----------------------  --------------
BPTL
-----------------------  --------------
CPU: requests            500m             
CPU: limits              500m
Memory: requests         500Mi
Memory: limits           500Mi
Storage                  Default
Replica count            2
-----------------------  --------------
Celery beat
-----------------------  --------------
CPU: requests            500m             
CPU: limits              500m
Memory: requests         750Mi
Memory: limits           750Mi
Storage                  Default
Replica count            1
-----------------------  --------------
Celery worker
-----------------------  --------------
CPU: requests            500m             
CPU: limits              500m
Memory: requests         750Mi
Memory: limits           750Mi
Storage                  Default
Replica count            2
-----------------------  --------------
Celery long-poll worker
-----------------------  --------------
CPU: requests            500m             
CPU: limits              500m
Memory: requests         1024Mi
Memory: limits           1024Mi
Storage                  Default
Replica count            2
-----------------------  --------------
Celery flower
-----------------------  --------------
CPU: requests            500m             
CPU: limits              500m
Memory: requests         500Mi
Memory: limits           500Mi
Storage                  Default
Replica count            1
-----------------------  --------------
Redis
-----------------------  --------------
CPU: requests            256m             
CPU: limits              256m
Memory: requests         64Mi
Memory: limits           128Mi
Storage                  20Gi
Replica count            1
=======================  ==============
