=========
CityLearn
=========

CityLearn is an open source OpenAI Gym environment for the implementation of Multi-Agent Reinforcement Learning (RL) for building energy coordination and demand response in cities :cite:p:`https://doi.org/10.48550/arxiv.2012.10504, 10.1145/3360322.3360998`. A major challenge for RL in demand response is the ability to compare algorithm performance :cite:p:`VAZQUEZCANTELI20191072`. Thus, CityLearn facilitates and standardizes the evaluation of RL agents such that different algorithms can be easily compared with each other.

.. image:: ../../assets/images/dr.jpg
   :scale: 30 %
   :alt: demand response
   :align: center

Districts and cities have periods of high demand for electricity, which raise electricity prices and the overall cost of the power distribution networks. Flattening, smoothening, and reducing the overall curve of electrical demand helps reduce operational and capital costs of electricity generation, transmission, and distribution networks. CityLearn allows the easy implementation of reinforcement learning agents in a single or multi-agent setting to reshape their aggregated curve of electrical demand by controlling the storage of energy by every agent.

Applications
************

CityLearn has been utilized in the following projects and publications:

.. csv-table::
   :file: ../../assets/tables/citylearn_applications.csv
   :header-rows: 1

.. toctree::
   :hidden:
   
   installation
   quickstart
   overview/index
   usage/index
   api/modules
   citylearn_challenge/index
   references

Cite CityLearn
**************

.. code-block:: bibtex

   @inproceedings{10.1145/3360322.3360998,
      author = {V\'{a}zquez-Canteli, Jos\'{e} R. and K\"{a}mpf, J\'{e}r\^{o}me and Henze, Gregor and Nagy, Zoltan},
      title = {CityLearn v1.0: An OpenAI Gym Environment for Demand Response with Deep Reinforcement Learning},
      year = {2019},
      isbn = {9781450370059},
      publisher = {Association for Computing Machinery},
      address = {New York, NY, USA},
      url = {https://doi.org/10.1145/3360322.3360998},
      doi = {10.1145/3360322.3360998},
      booktitle = {Proceedings of the 6th ACM International Conference on Systems for Energy-Efficient Buildings, Cities, and Transportation},
      pages = {356–357},
      numpages = {2},
      keywords = {Smart Grid, Building Energy Control, Smart Buildings},
      location = {New York, NY, USA},
      series = {BuildSys '19}
   }

Contributing
************

CityLearn is an open-source project that continues to benefit from community-driven updates and suggestion. Before you begin contributing please, read our `Contributor Covenant Code of Covenant <https://github.com/intelligent-environments-lab/CityLearn/blob/master/CODE_OF_CONDUCT.md>`_.

Visit the `CityLearn GitHub repository <https://github.com/intelligent-environments-lab/CityLearn>`_ to join the community and start contributing.

Refer to our `bug report template <https://github.com/intelligent-environments-lab/CityLearn/blob/master/.github/ISSUE_TEMPLATE/bug_report.md>`_ for guidelines on how to report bugs or `feature request template <https://github.com/intelligent-environments-lab/CityLearn/blob/master/.github/ISSUE_TEMPLATE/feature_request.md>`_ to propose enhancements and functionalities that you will like to be implemented.

Indices and tables
******************

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
