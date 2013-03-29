import xmlrpclib
# only one api server so we'll use the deutschland mirror for downloading
client = xmlrpclib.ServerProxy('http://pypi.python.org/pypi')
packages = client.list_packages()

import tarfile, re, requests, csv, json
from base64 import b64encode

def _extract_deps(content):
    """ Extract dependencies using install_requires directive """
    results = re.findall("install_requires=\[([\W'a-zA-Z0-9]*?)\]", content, re.M)
    deps = []
    if results:
        deps = [a.replace("'", "").strip() 
                for a in results[0].strip().split(",") 
                if a.replace("'", "").strip() != ""]
    return deps
    
def _extract_setup_content(package_file):
    """Extract setup.py content as string from downladed tar """
    tar_file = tarfile.open(fileobj=package_file)
    setup_candidates = [elem for elem in tar_file.getmembers() if 'setup.py' in elem.name]
    if len(setup_candidates) == 1:
        setup_member = setup_candidates[0]
        content = tar_file.extractfile(setup_member).read()
        return content
    else:
        print "Too few candidates or too many for setup.py in tar" 
        return None
    
def extract_package(name, client = xmlrpclib.ServerProxy('http://pypi.python.org/pypi')):
    with open('pypi-deps.csv', 'a') as file:
        spamwriter = csv.writer(file, delimiter='\t',
                            quotechar='|', quoting=csv.QUOTE_MINIMAL)
        for release in client.package_releases(name):
            #print "Extracting %s release %s" % (name, release) 
            doc = client.release_urls(name, release)
            if doc:
                url = doc[0].get('url').replace("http://pypi.python.org/", "http://f.pypi.python.org/")
                #print "Downloading url %s" % url
                req = requests.get(url)
                if req.status_code != 200:
                    print "Could not download file %s" % req.status_code
                else:
                    with open('/tmp/temp_tar', 'w') as tar_file:
                        tar_file.write(req.content)
                    with open('/tmp/temp_tar', 'r') as tar_file:
                        try:
                            content = _extract_setup_content(tar_file)
                        except:
                            content = None
                    if content:
                        spamwriter.writerow([name, release, b64encode(json.dumps(_extract_deps(content)))])
# main processing
for package in packages:
    extract_package(package, client)

# graph creation
import networkx as nx, json
from base64 import b64decode

data = []
G=nx.Graph()
with open('pypi-deps.csv', 'r') as file:
    for line in file:
        name, version, deps = line.split('\t')
        deps = json.loads(b64decode(deps))
        data+= [(name, version, deps)]

for ex in data:
    name, version, deps = ex
    G.add_node("%s-%s" % (name, version))
    for dep in deps:
        if not '#' in dep: G.add_edge("%s-%s" % (name, version), dep.replace("\"", ""))

nx.write_gml(G, 'test.gml')
