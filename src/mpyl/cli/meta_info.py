"""Extractors for package meta information"""

import os
from importlib.metadata import distribution

import click

from . import get_version

VDB_LOGO = """
                                         .::.               
                                         :~~~^:.            
                                         ^~~~~~~^:.         
               .........................:~~~~~~~~~^^.       
             .^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^:.    
             .^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^:. 
               ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~:
                :~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^:. 
                 :~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~~~~~^:.    
                  .^~~~~~~~~~~~~^........^~~~~~~~~^:.       
                   .^~~~~~~~~~~~~^       ^~~~~~^^.          
                     ^~~~~~~~~~~~~^.     :~~^^:.            
                      :~~~~~~~~~~~~^.     ::.               
                       :~~~~~~~~~~~~~:                      
                        .^~~~~~~~~~~~~:                     
      .::^^^^^^::.       .^~~~~~~~~~~~~^                    
   .:^~~~~~~~~~~~~^:.      ^~~~~~~~~~~~~^.                  
  :^~~~~~~~~~~~~~~~~^:::::::^~~~~~~~~~~~~^.                 
 :~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~.                
.^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~:               
.~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~:              
 ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^             
 .~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^.            
  .^~~~~~~~~~~~~~~~~^:........................              
    .:^~~~~~~~~~~^^.                                        
       .:::^^:::.
"""


def simple_version():
    return f"MPyL {get_version()}"


def about():
    dist = distribution('mpyl')
    details = os.linesep.join(str(dist.metadata).split(os.linesep)[1:16])
    return f'{details}{VDB_LOGO}'


@click.command()
@click.option('--verbose', '-v', is_flag=True, default=False, help="Print more output.")
def version(verbose):
    """Version information"""
    if verbose:
        click.echo(about())
    else:
        click.echo(simple_version())
