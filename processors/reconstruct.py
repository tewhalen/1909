#!/usr/bin/env python3
import csv
import click
import pathlib
import pandas
import jinja2
import re
import ast
template = """
<!DOCTYPE html>
<html>
<head>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet" 
integrity="sha384-1BmE4kWBq78iYhFldvKuhfTAU6auU8tT94WrHftjDbrCEXSU1oBoqyl2QvZ6jIW3" crossorigin="anonymous">
<style>
  
  .address {
      width:250px;
      font-size: smaller;
      padding: 0;
  }
  .address td 
  {
    text-align: right;
    font-family: monospace;
    padding: 0;
    
  }
  .address th
  {text-align: center;}

   #visualizer
  {position: relative;
    top:0px;
    visibility: visible;
  border:2px solid green;
  height:30px;
  width:100px;
  opacity: 25%;
  background: green;
  }

  #column_img
  {position: absolute;}

   .unsure {
    color: red;
    font-weight: bold;
  }
</style>
</head>
<body>
<script src="jquery-3.6.0.min.js"></script>
<script>
       $( document ).ready(function() {
        $("td").hover(function(){

                        var scale = document.getElementById("column_img").width / document.getElementById("column_img").naturalWidth;
                        $("#visualizer").css("visibility", "visible");
                        $("#visualizer").css("top", this.dataset.top * scale);
                        $("#visualizer").css("width", this.dataset.width * scale);
                        $("#visualizer").css("left", this.dataset.left * scale);
                        $("#visualizer").css("height", this.dataset.height * scale);

                      }, 
                      
                      function(){
                        $("#visualizer").css("visibility", "hidden");

        });
    });
    </script>
<div class="container">
<div class="row align-items-start">
<div class="col">
<img id="column_img" src="{{column_image}}" width="300px"/>
<div id="visualizer"></div>
</div>
<div class="col">
<table class="address table table-bordered table-sm">
{% for street_name, group in streets %}
  <tr><th colspan=4>{{street_name}}</th></tr>
  {% for i in range(group['line_num'].min(), group['line_num'].max()) %}
  <tr>
    {% for j, row in group[group['line_num'] == i].iterrows() %}
    <td data-left="{{row.new_bbox[0]}}" data-top="{{row.new_bbox[1]}}" 
    data-height="{{row.new_bbox[3]-row.new_bbox[1]}}" 
    data-width="{{row.new_bbox[2]-row.new_bbox[0]}}"
    {% if row.new_conf < 90 %}
    class="unsure"
    {% endif %}
    >
    {{row['new'] | int}}
    
    </td>
    <td data-left="{{row.old_bbox[0]}}" data-top="{{row.old_bbox[1]}}" 
    data-height="{{row.old_bbox[3]-row.old_bbox[1]}}" 
    data-width="{{row.old_bbox[2]-row.old_bbox[0]}}"
    {% if row.old_conf < 90 %}
    class="unsure"
    {% endif %}>
    
    {{row['old']}}</td>
    {% endfor %}
  </tr>
  {% endfor %}
{% endfor %}
</table>
</div>
</div>
</div>
</body>
</html>
"""



@click.command()
@click.argument("infile",type=click.Path(exists=True, path_type=pathlib.Path))
def reconstruct(infile:pathlib.Path):
    """Using a CSV file, reconstruct what the column may have looked like"""
    csv_in = pandas.read_csv(infile, converters={"new_bbox": ast.literal_eval, "old_bbox":ast.literal_eval})
    

    column_id = int(re.match(r"column-([0-9]+)", infile.name).group(1))

    column_image = infile.with_name("column-{}.png".format(column_id))
    t = jinja2.Template(template)

    data = {}
   
    print(t.render(streets=csv_in.groupby('street'),
    column_image=column_image))
    

if __name__ == '__main__':
    reconstruct()