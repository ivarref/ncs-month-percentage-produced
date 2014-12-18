#!/usr/bin/python
# -*- coding: utf-8 -*-
from decimal import Decimal
import datetime
import sys
import codecs

production_url_csv = 'http://factpages.npd.no/ReportServer?/FactPages/TableView/field_production_monthly&rs:Command=Render&rc:Toolbar=false&rc:Parameters=f&rs:Format=CSV&Top100=false&IpAddress=84.208.160.74&CultureCode=en'

reserves_url_csv = 'http://factpages.npd.no/ReportServer?/FactPages/TableView/field_reserves&rs:Command=Render&rc:Toolbar=false&rc:Parameters=f&rs:Format=CSV&Top100=false&IpAddress=84.208.160.74&CultureCode=en'

def set_output_encoding(encoding='utf-8'):
  import sys
  import codecs
  '''When piping to the terminal, python knows the encoding needed, and
     sets it automatically. But when piping to another program (for example,
     | less), python can not check the output encoding. In that case, it 
     is None. What I am doing here is to catch this situation for both 
     stdout and stderr and force the encoding'''
  current = sys.stdout.encoding
  if current is None :
    sys.stdout = codecs.getwriter(encoding)(sys.stdout)
  current = sys.stderr.encoding
  if current is None :
    sys.stderr = codecs.getwriter(encoding)(sys.stderr)

def get_url(url):
  import urllib2
  import hashlib
  import os

  m = hashlib.md5()
  m.update(url)
  md5 = m.hexdigest()
  cache = 'cache/' + md5
  if not os.path.exists('cache'):
    os.makedirs('cache')

  if not os.path.isfile(cache):
    with codecs.open(cache, encoding='utf-8', mode='w') as fd:
      print "Creating cache %s for %s ..." % (cache, url)
      response = urllib2.urlopen(url)
      fd.write(response.read().decode('utf-8-sig'))
      print "Created cache %s for %s" % (cache, url)
  
  with open(cache, 'r') as fd:
    return fd.read().decode('utf-8')

set_output_encoding()

(fldName,fldRecoverableOil,fldRecoverableGas,fldRecoverableNGL,fldRecoverableCondensate,fldRecoverableOE,fldRemainingOil,fldRemainingGas,fldRemainingNGL,fldRemainingCondensate,fldRemainingOE,fldDateOffResEstDisplay,fldNpdidField,DatesyncNPD) = tuple([idx for (idx, x) in enumerate("fldName,fldRecoverableOil,fldRecoverableGas,fldRecoverableNGL,fldRecoverableCondensate,fldRecoverableOE,fldRemainingOil,fldRemainingGas,fldRemainingNGL,fldRemainingCondensate,fldRemainingOE,fldDateOffResEstDisplay,fldNpdidField,DatesyncNPD".split(","))])

(prfInformationCarrier,prfYear,prfMonth,prfPrdOilNetMillSm3,prfPrdGasNetBillSm3,prfPrdNGLNetMillSm3,prfPrdCondensateNetMillSm3,prfPrdOeNetMillSm3,prfPrdProducedWaterInFieldMillSm3,prfNpdidInformationCarrier) = tuple([idx for (idx, x) in enumerate("prfInformationCarrier,prfYear,prfMonth,prfPrdOilNetMillSm3,prfPrdGasNetBillSm3,prfPrdNGLNetMillSm3,prfPrdCondensateNetMillSm3,prfPrdOeNetMillSm3,prfPrdProducedWaterInFieldMillSm3,prfNpdidInformationCarrier".split(","))])

# *** configuration ***
#(resource, recoverable_resource) = (prfPrdGasNetBillSm3, fldRecoverableGas)
(resource, recoverable_resource) = (prfPrdOilNetMillSm3, fldRecoverableOil)
# *** end of configuration ***


def get_reserves_map():
  reserves = get_url(reserves_url_csv)

  reserves = [line.split(",") for line in reserves.split("\n")[1:] if line.strip() != '']
  reserves_map = {}
  for r in reserves:
    reserves_map[r[fldName]] = Decimal(r[recoverable_resource])
  #Om jeg husker riktig så pågår det ”prøveproduksjon” fra ”Delta 33/9-6". Funnet ble gjort i 1976 er nå formelt vedtatt utbygd og estimert utvinnbart er rundt 0,074 millioner Sm3 (0,47 millioner fat) olje.
  reserves_map[u'33/9-6 DELTA'] = Decimal('0.074')
  return reserves_map

reserves_map = get_reserves_map()

production_data = [line.split(",") for line in get_url(production_url_csv).split("\n")[1:] if not line.strip() == '']

field_to_decade = {}


def have_resource(data):
  return any([line[resource] > 0 for line in data])

def decade(data):
  return int(data[prfYear]) - (int(data[prfYear]) % 10)

for line in production_data:
  line[resource] = Decimal(line[resource])
  field = line[prfInformationCarrier] 
  if field not in field_to_decade:
    field_to_decade[field] = decade(line)

distinct_decades = list(set([decade(line) for line in production_data]))
distinct_decades.sort()

distinct_decades.append(0)

def fields_of_decade(dec):
  fields = list(set([k for (k, v) in field_to_decade.items() if (v == dec) or (dec==0)]))
  fields.sort()
  return fields

def decade_production(dec):
  fields = fields_of_decade(dec)
  return [line for line in production_data if line[prfInformationCarrier] in fields]
  
def date_str(data):
  return "%s-%02d" % (data[prfYear], int(data[prfMonth]))
  
with codecs.open('data/data.tsv', encoding='utf-8', mode='w') as fd:
  fd.write('decade\tmonth\tpercentage_produced\n')

  for dec in distinct_decades:
    print dec,
    sys.stdout.flush()
    prod = decade_production(dec)
    dates = list(set([date_str(p) for p in prod]))
    dates.sort()
    reserves = sum([reserves_map[field] for field in fields_of_decade(dec)])
    cumulative = Decimal(0)
    dato_to_lines = {}

    for line in prod:
      key = date_str(line)
      if not key in dato_to_lines:
        dato_to_lines[key] = []
      dato_to_lines[key].append(line[resource])

    for (idx, dato) in enumerate(dates):
      sys.stdout.write(".")
      sys.stdout.flush()
      cumulative += sum(dato_to_lines[dato])
      dec_str = str(dec)
      if dec == 0:
        dec_str = "All"
      fd.write('%s\t%d\t%.02f\n' % (dec_str, idx, Decimal(100.0) * cumulative / reserves))
    print " the fields used was: %s" % (", ".join(fields_of_decade(dec))),
    print "\n"

  pass

