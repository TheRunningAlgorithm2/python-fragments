# Deliberately unformatted: run `fragments format --input examples/formatting.py`
# to see Black tidy the Python while leaving every fragment exactly as written.
import os,sys
from typing import   Optional


# 1. Quote style, spacing and blank lines
def  greeting(name:str,punctuation = '!')->str:
    prefix   ='Hello'
    return prefix+', '+name+punctuation
class Page:
    title:str='Home'
    def __init__(self,items:list[str]):
        self.items=items


# 2. Long calls and collections are split one item per line with trailing commas
SETTINGS = {'debug':True,'host':'localhost','port':8000,'allowed_hosts':['localhost','example.com'],'secret':os.environ.get('SECRET')}

def build_url(scheme:str,host:str,port:int,path:str,query:Optional[dict[str,str]]=None)->str:
    return scheme+'://'+host+':'+str(port)+path+('?'+'&'.join(f'{key}={value}' for key,value in (query or {}).items()) if query else '')


# 3. Fragments are untouched: odd indentation, spacing and quotes stay as written
def Card(title:str,items:list[str])->str:
    return <>
        <div   class="card">
              <h2>{{title}}</h2>
            <ul>
                <li for={{item in items}}>{{  item  }}</li>
            </ul>
        </div>
    </>


# 4. Fragments inline in expressions: surrounding Python is formatted, fragment is not
def render_all(pages:list[Page])->list[str]:
    return [ <><p   class="row">{{page.title}}</p></> for page in pages if page.items ]

def Row(label:str,value:str)->str:  return <><tr><td>{{label}}</td><td>{{value}}</td></tr></>


# 5. Conditionals and trailing-comma handling
def describe(count:int)->str:
    if count==0: return 'none'
    elif count<10:
        return 'few'
    else :
        return 'many'

if __name__=='__main__':
    print(Card('Fruit',['apple','pear']));print(greeting('world'))
