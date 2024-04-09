=======
factors
=======

Generate actuarial factors for several Dutch tables like AG2014, AG2016, AG2018, AG2020, AG2022, etc.

1. Installation
------------

Create a virtual environment:

.. code-block:: console

    mkdir actfact
    cd actfact
    python3 -m venv venv
    source venv/bin/activate

Install the factors package:

.. code-block:: console

    pip install git+https://github.com/Oxylo/factors.git@master

And for running the code interactively, install Jupyter notebook:

.. code-block:: console

    pip install notebook

2. Examples
------------

.. code-block:: console
   :caption: Generate actuarial factors for specific LifeTable at fixed intrest rate

    from factors import LifeTable
    lifetab = LifeTable("AG2022", calc_year=2022)
    all_tabs = lifetab.calculate_factors(intrest=2, pension_age=68)


.. code-block:: console
   :caption: Generate table with cash flows, useful when using yield curves 

    from factors import LifeTable
    lifetab = LifeTable("AG2018", calc_year=2020)
    opll = lifetab.cf_retirement_pension(age_insured=68, sex_insured='M', pension_age=68)
    npll = lifetab.cf_defined_partner(age_insured=65,sex_insured='F',pension_age=68)
    npll_od = lifetab.cf_undefined_partner(age_insured=65,sex_insured='F',pension_age=68)
    df = pd.DataFrame({'OPLL': opll['payments'], 'NPLL': npll['payments'], 'NPLL_ondefined': npll_od['payments']})
    all_tabs = lifetab.calculate_factors(intrest=2, pension_age=68)


.. code-block:: console
   :caption: Compare life expectancy of two different tables at the calculation year of the most recent table

    from factors import LifeTable
    tab2014 = LifeTable("AG2014", calc_year=2016)
    life_expectancy_ag2014 = tab2014.lx(current_age=0)['M'].sum()
    tab2016 = LifeTable("AG2016", calc_year=2016)
    life_expectancy_ag2016 = tab2016.lx(current_age=0)['M'].sum()

.. code-block:: console
   :caption: Run unit tests

    from factors import LifeTable
    tab = LifeTable("AG2022", calc_year=2022)
    tab.run_test()




     

