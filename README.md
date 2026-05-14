# render-docs
YAML to MD that will support turning YAML designs into GH suitable markdown

# Requirements 
There is no actual installation required. The script should be executable from 
wherever you extract it. It does require the following dependencies, which are 
probably already part of any app you would want to us it alongside: 

- PyYAML
- requests

# installation
There really isn't any need to clone the repo unless you want to edit either 
the template or the script itself. Just copy the file to someplace that is in 
your PATH: 

```bash
mkdir -p ~/bin && \
    wget -qO ~/bin/render_docs https://raw.githubusercontent.com/carrollaboratory/render-docs/refs/heads/main/render_docs.py && \
    chmod +x ~/bin/render_docs
```

# Usage

## Blank/New Design Document
To create a new Design YAML file, simply run the script with the --template flag: 

```bash
render_docs --template > docs/design.yaml
```

## Render YAML into MD
Just tell the script where to write the markdown and pass the YAML in as a 
positional argument
```bash
render_docs -o docs/DESIGN.md docs/design.yaml
```
