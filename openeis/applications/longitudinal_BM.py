from openeis.applications import DriverApplicationBaseClass, InputDescriptor, OutputDescriptor, ConfigDescriptor
import logging
from django.db.models import Sum

"""
    Longitudinal benchmarking application will aggregate data over the year
    and will output amounts according to the year.  This data is to be put
    into a bar graph so user can easily see trends happening over the years.
"""

class Application(DriverApplicationBaseClass):

    def __init__(self, *args, building_sq_ft=-1, building_name=None,**kwargs):
        #Called after app has been staged
        """
        When applications extend this base class, they need to make
        use of any kwargs that were setup in config_param
        """
        super().__init__(*args,**kwargs)

        self.default_building_name_used = False

        #match parameters
        if building_sq_ft < 0:
            raise Exception("Invalid input for building_sq_ft")
        if building_name is None:
            building_name = "None supplied"
            self.default_building_name_used = True

        self.sq_ft = building_sq_ft
        self.building_name = building_name



    @classmethod
    def get_config_parameters(cls):
        #Called by UI
        #also matches parameters
        return {
                    "building_sq_ft": ConfigDescriptor(float, "Square footage",\
                            minimum=200),
                    "building_name": ConfigDescriptor(str, "Building Name",\
                            optional=True)
               }


    @classmethod
    def required_input(cls):
        #Called by UI
        return {
                    'load':InputDescriptor('WholeBuildingEnergy',\
                            'Building Load'),
                    'natgas':InputDescriptor('NaturalGas', 'Natural Gas usage')
                }

    """
    Output is the year with its respective load and natural gas amounts
    aggregated over the year.
    """
    @classmethod
    def output_format(cls, input_object):
        #Called when app is staged
        topics = input_object.get_topics()
        load_topic = topics['load'][0]
        load_topic_parts = load_topic.split('/')
        output_topic_base = load_topic_parts[:-1]
        year_topic = '/'.join(output_topic_base+['longitudinalbm', 'time'])
        load_topic = '/'.join(output_topic_base+['longitudinalbm', 'load'])
        gas_topic = '/'.join(output_topic_base+['longitudinalbm', 'natgas'])

        #stuff needed to put inside output, will output by row, each new item
        #is a new file, title must match title in execute when writing to out
        output_needs =  {
                         'LongitudinalBM':
                            {'year':OutputDescriptor('int', year_topic),
                             'load':OutputDescriptor('float', load_topic),
                            'natgas':OutputDescriptor('float', gas_topic)}
                        }

        return output_needs

    def report(self):
        #Called by UI to create Viz
        """Describe how to present output to user
        Display this viz with these columns from this table


        display elements is a list of display objects specifying viz and columns
        for that viz
        """
        display_elements = []

        return display_elements

    def execute(self):
        #Called after User hits GO
        """
        Will output the following: year, aggregated load amounts,
        and aggregated gas amounts.
        """
        self.out.log("Starting analysis", logging.INFO)

        #grabs data by year and reduces it
        load_by_year = self.inp.get_query_sets('load', group_by='year', \
                                               group_by_aggregation=Sum, \
                                               exclude={'value':None},
                                               wrap_for_merge=True)

        gas_by_year = self.inp.get_query_sets('natgas', group_by='year', \
                                              group_by_aggregation=Sum, \
                                              exclude={'value':None},
                                              wrap_for_merge=True)

        merge_load_gas = self.inp.merge(load_by_year, gas_by_year)

        for x in merge_load_gas:
            self.out.insert_row("LongitudinalBM", \
                                {'year': x['time'],
                                 'load': x['load'][0], \
                                'natgas': x['natgas'][0]})

