"""Extractors for package meta information"""

import os
from importlib.metadata import distribution

import click

from . import get_version
from ..projects.versioning import get_latest_release

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
    binary_version = get_version()
    release = get_latest_release()
    release_text = (
        f"\nLatest public release {release}" if binary_version != release else ""
    )
    return f"MPyL {binary_version}{release_text}"


def about():
    dist = distribution("mpyl")
    details = os.linesep.join(str(dist.metadata).split(os.linesep)[1:16])
    return f"{details}{VDB_LOGO}"


@click.command()
@click.option("--verbose", "-v", is_flag=True, default=False, help="Print more output.")
def version(verbose):
    """Version information"""
    if verbose:
        click.echo(about())
    else:
        click.echo(simple_version())
