# -*- coding: utf-8 -*-
# Daum Movie

import urllib, unicodedata

DAUM_MOVIE_SRCH   = "http://movie.daum.net/data/movie/search/v2/movie.json?size=20&start=1&searchText=%s"

DAUM_MOVIE_DETAIL = "http://movie.daum.net/moviedb/main?movieId=%s"
# DAUM_MOVIE_DETAIL = "http://movie.daum.net/data/movie/movie_info/detail.json?movieId=%s"
DAUM_MOVIE_CAST   = "http://movie.daum.net/data/movie/movie_info/cast_crew.json?pageNo=1&pageSize=100&movieId=%s"
DAUM_MOVIE_PHOTO  = "http://movie.daum.net/data/movie/photo/movie/list.json?pageNo=1&pageSize=100&id=%s"

DAUM_TV_SRCH      = "https://search.daum.net/search?w=tot&q=%s"
DAUM_TV_DETAIL    = "http://movie.daum.net/tv/main?tvProgramId=%s"
DAUM_TV_CAST      = "http://movie.daum.net/tv/crew?tvProgramId=%s"
DAUM_TV_PHOTO     = "http://movie.daum.net/data/movie/photo/tv/list.json?pageNo=1&pageSize=100&id=%s"
DAUM_TV_EPISODE   = "http://movie.daum.net/tv/episode?tvProgramId=%s"

IMDB_TITLE_SRCH   = "http://www.google.com/search?q=site:imdb.com+%s"
TVDB_TITLE_SRCH   = "http://thetvdb.com/api/GetSeries.php?seriesname=%s"

RE_YEAR_IN_NAME   =  Regex('\((\d+)\)')
RE_MOVIE_ID       =  Regex("movieId=(\d+)")
RE_TV_ID          =  Regex("tvProgramId=(\d+)")
RE_PHOTO_SIZE     =  Regex("/C\d+x\d+/")
RE_IMDB_ID        =  Regex("/(tt\d+)/")

JSON_MAX_SIZE     = 10 * 1024 * 1024

DAUM_CR_TO_MPAA_CR = {
    u'전체관람가': {
        'KMRB': 'kr/A',
        'MPAA': 'G'
    },
    u'12세이상관람가': {
        'KMRB': 'kr/12',
        'MPAA': 'PG'
    },
    u'15세이상관람가': {
        'KMRB': 'kr/15',
        'MPAA': 'PG-13'
    },
    u'청소년관람불가': {
        'KMRB': 'kr/R',
        'MPAA': 'R'
    },
    u'제한상영가': {     # 어느 여름날 밤에 (2016)
        'KMRB': 'kr/X',
        'MPAA': 'NC-17'
    }
}

def Start():
  HTTP.CacheTime = CACHE_1HOUR * 12
  HTTP.Headers['Accept'] = 'text/html, application/json'

####################################################################################################
def searchDaumMovie(results, media, lang):
  media_name = media.name
  media_name = unicodedata.normalize('NFKC', unicode(media_name)).strip()
  Log.Debug("search: %s %s" %(media_name, media.year))

  data = JSON.ObjectFromURL(url=DAUM_MOVIE_SRCH % (urllib.quote(media_name.encode('utf8'))))
  items = data['data']
  for item in items:
    year = str(item['prodYear'])
    title = String.DecodeHTMLEntities(String.StripTags(item['titleKo'])).strip()
    id = str(item['movieId'])
    if year == media.year:
      score = 95
    elif len(items) == 1:
      score = 80
    else:
      score = 10
    Log.Debug('ID=%s, media_name=%s, title=%s, year=%s, score=%d' %(id, media_name, title, year, score))
    results.Append(MetadataSearchResult(id=id, name=title, year=year, score=score, lang=lang))

def searchDaumTV(results, media, lang):
  media_name = media.show
  media_name = unicodedata.normalize('NFKC', unicode(media_name)).strip()
  Log.Debug("search: %s %s" %(media_name, media.year))

  html = HTML.ElementFromURL(DAUM_TV_SRCH % urllib.quote(media_name.encode('utf8')))
  tvp = html.xpath('//div[@id="tvpColl"]')[0]
  if tvp:
    items = []
    a = tvp.xpath('//a[@class="tit_info"]')[0]
    id = Regex('irk=(\d+)').search(a.get('href')).group(1)
    title = a.text.strip()
    year = Regex('(\d{4})\.\d+.\d+~').search(tvp.xpath('//div[@class="head_cont"]//span[@class="txt_summary"][last()]')[0].text).group(1)
    items.append({ 'id': id, 'title': title, 'year': year })

    spans = tvp.xpath(u'//div[contains(@class,"coll_etc")]//span[.="(동명프로그램)"]')
    for span in spans:
      year = Regex('(\d{4})').search(span.xpath('./preceding-sibling::span[1]')[0].text).group(1)
      a = span.xpath('./preceding-sibling::a[1]')[0]
      id = Regex('irk=(\d+)').search(a.get('href')).group(1)
      title = a.text.strip()
      items.append({ 'id': id, 'title': title, 'year': year })

    for item in items:
      if item['year'] == media.year:
        score = 95
      elif len(items) == 1:
        score = 80
      else:
        score = 10
      Log.Debug('ID=%s, media_name=%s, title=%s, year=%s, score=%d' %(item['id'], media_name, item['title'], item['year'], score))
      results.Append(MetadataSearchResult(id=item['id'], name=item['title'], year=item['year'], score=score, lang=lang))

def updateDaumMovie(metadata):
  # (1) from detail page
  poster_url = None

  try:
    html = HTML.ElementFromURL(DAUM_MOVIE_DETAIL % metadata.id)
    title = html.xpath('//div[@class="subject_movie"]/strong')[0].text
    match = Regex('(.*?) \((\d{4})\)').search(title)
    metadata.title = match.group(1)
    metadata.year = int(match.group(2))
    metadata.original_title = html.xpath('//span[@class="txt_movie"]')[0].text
    metadata.rating = float(html.xpath('//em[@class="emph_grade"]')[0].text)
    # 장르
    metadata.genres.clear()
    dds = html.xpath('//dl[contains(@class, "list_movie")]/dd')
    for genre in dds.pop(0).text.split('/'):
        metadata.genres.add(genre)
    # 나라
    metadata.countries.clear()
    for country in dds.pop(0).text.split(','):
        metadata.countries.add(country.strip())
    # 개봉일 (optional)
    match = Regex(u'(\d{4}\.\d{2}\.\d{2})\s*개봉').search(dds[0].text)
    if match:
      metadata.originally_available_at = Datetime.ParseDate(match.group(1)).date()
      dds.pop(0)
    # 재개봉 (optional)
    match = Regex(u'(\d{4}\.\d{2}\.\d{2})\s*\(재개봉\)').search(dds[0].text)
    if match:
      dds.pop(0)
    # 상영시간, 등급 (optional)
    match = Regex(u'(\d+)분(?:, (.*?)\s*$)?').search(dds.pop(0).text)
    if match:
      metadata.duration = int(match.group(1))
      cr = match.group(2)
      if cr:
        match = Regex(u'미국 (.*) 등급').search(cr)
        if match:
          metadata.content_rating = match.group(1)
        elif cr in DAUM_CR_TO_MPAA_CR:
          metadata.content_rating = DAUM_CR_TO_MPAA_CR[cr]['MPAA' if Prefs['use_mpaa'] else 'KMRB']
        else:
          metadata.content_rating = 'kr/' + cr
    # Log.Debug('genre=%s, country=%s' %(','.join(g for g in metadata.genres), ','.join(c for c in metadata.countries)))
    # Log.Debug('oaa=%s, duration=%s, content_rating=%s' %(metadata.originally_available_at, metadata.duration, metadata.content_rating))
    metadata.summary = '\n'.join(txt.strip() for txt in html.xpath('//div[@class="desc_movie"]/p//text()'))
    poster_url = html.xpath('//img[@class="img_summary"]/@src')[0]
  except Exception, e:
    Log.Debug(repr(e))
    pass

  # (2) cast crew
  directors = list()
  producers = list()
  writers = list()
  roles = list()

  data = JSON.ObjectFromURL(url=DAUM_MOVIE_CAST % metadata.id)
  for item in data['data']:
    cast = item['castcrew']
    if cast['castcrewCastName'] in [u'감독', u'연출']:
      director = dict()
      director['name'] = item['nameKo'] if item['nameKo'] else item['nameEn']
      if item['photo']['fullname']:
        director['photo'] = item['photo']['fullname']
      directors.append(director)
    elif cast['castcrewCastName'] == u'제작':
      producer = dict()
      producer['name'] = item['nameKo'] if item['nameKo'] else item['nameEn']
      if item['photo']['fullname']:
        producer['photo'] = item['photo']['fullname']
      producers.append(producer)
    elif cast['castcrewCastName'] in [u'극본', u'각본']:
      writer = dict()
      writer['name'] = item['nameKo'] if item['nameKo'] else item['nameEn']
      if item['photo']['fullname']:
        writer['photo'] = item['photo']['fullname']
      writers.append(writer)
    elif cast['castcrewCastName'] in [u'주연', u'조연', u'출연', u'진행']:
      role = dict()
      role['role'] = cast['castcrewTitleKo']
      role['name'] = item['nameKo'] if item['nameKo'] else item['nameEn']
      if item['photo']['fullname']:
        role['photo'] = item['photo']['fullname']
      roles.append(role)
    # else:
    #   Log.Debug("unknown role: castcrewCastName=%s" % cast['castcrewCastName'])

  if directors:
    metadata.directors.clear()
    for director in directors:
      meta_director = metadata.directors.new()
      if 'name' in director:
        meta_director.name = director['name']
      if 'photo' in director:
        meta_director.photo = director['photo']
  if producers:
    metadata.producers.clear()
    for producer in producers:
      meta_producer = metadata.producers.new()
      if 'name' in producer:
        meta_producer.name = producer['name']
      if 'photo' in producer:
        meta_producer.photo = producer['photo']
  if writers:
    metadata.writers.clear()
    for writer in writers:
      meta_writer = metadata.writers.new()
      if 'name' in writer:
        meta_writer.name = writer['name']
      if 'photo' in writer:
        meta_writer.photo = writer['photo']
  if roles:
    metadata.roles.clear()
    for role in roles:
      meta_role = metadata.roles.new()
      if 'role' in role:
        meta_role.role = role['role']
      if 'name' in role:
        meta_role.name = role['name']
      if 'photo' in role:
        meta_role.photo = role['photo']

  # (3) from photo page
  url_tmpl = DAUM_MOVIE_PHOTO
  data = JSON.ObjectFromURL(url=url_tmpl % metadata.id)
  max_poster = int(Prefs['max_num_posters'])
  max_art = int(Prefs['max_num_arts'])
  idx_poster = 0
  idx_art = 0
  for item in data['data']:
    if item['photoCategory'] == '1' and idx_poster < max_poster:
      art_url = item['fullname']
      if not art_url: continue
      #art_url = RE_PHOTO_SIZE.sub("/image/", art_url)
      idx_poster += 1
      try: metadata.posters[art_url] = Proxy.Preview(HTTP.Request(item['thumbnail']), sort_order = idx_poster)
      #try: metadata.posters[art_url] = Proxy.Preview(HTTP.Request(item['thumbnail'], None, { 'Referer': url_tmpl }), sort_order = idx_poster)
      except: pass
    elif item['photoCategory'] in ['2', '50'] and idx_art < max_art:
      art_url = item['fullname']
      if not art_url: continue
      #art_url = RE_PHOTO_SIZE.sub("/image/", art_url)
      idx_art += 1
      try: metadata.art[art_url] = Proxy.Preview(HTTP.Request(item['thumbnail']), sort_order = idx_art)
      #try: metadata.art[art_url] = Proxy.Preview(HTTP.Request(item['thumbnail'], None, { 'Referer': url_tmpl }), sort_order = idx_art)
      except: pass
  Log.Debug('Total %d posters, %d artworks' %(idx_poster, idx_art))
  if idx_poster == 0:
    if poster_url:
      poster = HTTP.Request( poster_url )
      try: metadata.posters[poster_url] = Proxy.Media(poster)
      except: pass
    # else:
    #   url = 'http://m.movie.daum.net/m/tv/main?tvProgramId=%s' % metadata.id
    #   html = HTML.ElementFromURL( url )
    #   arts = html.xpath('//img[@class="thumb_program"]')
    #   for art in arts:
    #     art_url = art.attrib['src']
    #     if not art_url: continue
    #     art = HTTP.Request( art_url )
    #     idx_poster += 1
    #     metadata.posters[art_url] = Proxy.Preview(art, sort_order = idx_poster)

    # (5) fill missing info
    # if Prefs['override_tv_id'] != 'None':
    #   page = HTTP.Request(DAUM_TV_DETAIL2 % metadata.id).content
    #   match = Regex('<em class="title_AKA"> *<span class="eng">([^<]*)</span>').search(page)
    #   if match:
    #     metadata.original_title = match.group(1).strip()

def updateDaumTV(metadata):
  # (1) from detail page
  poster_url = None

  try:
    html = HTML.ElementFromURL(DAUM_TV_DETAIL % metadata.id)
    metadata.title = html.xpath('//div[@class="subject_movie"]/strong')[0].text
    metadata.original_title = ''
    metadata.rating = float(html.xpath('//div[@class="subject_movie"]/div/em')[0].text)
    metadata.genres.clear()
    metadata.genres.add(html.xpath('//dl[@class="list_movie"]/dd[2]')[0].text)
    metadata.studio = html.xpath('//dl[@class="list_movie"]/dd[1]/em')[0].text
    match = Regex('(\d{4}\.\d{2}\.\d{2})~(\d{4}\.\d{2}\.\d{2})?').search(html.xpath('//dl[@class="list_movie"]/dd[4]')[0].text)
    if match:
      metadata.originally_available_at = Datetime.ParseDate(match.group(1)).date()
    metadata.summary = String.DecodeHTMLEntities(String.StripTags(html.xpath('//div[@class="desc_movie"]')[0].text).strip())
    poster_url = html.xpath('//img[@class="img_summary"]/@src')[0]
  except Exception, e:
    Log.Debug(repr(e))
    pass

  # (2) cast crew
  directors = list()
  producers = list()
  writers = list()
  roles = list()

  try:
    html = HTML.ElementFromURL(DAUM_TV_CAST % metadata.id)
    for item in html.xpath('//a[@class="link_join"]'):
      cast = dict()
      cast['name'] = item.xpath('.//*[@class="tit_join"]/em/text()')[0]
      match = Regex(u'^(.*?)( 역)?$').search(item.xpath('.//*[@class="txt_join"]/text()')[0])
      cast['role'] = match.group(1)
      src = item.xpath('.//img[@class="thumb_photo"]/@src')
      cast['photo'] = src[0] if src else None

      if cast['role'] in [u'감독', u'연출']:
        directors.append(cast)
      elif cast['role'] == u'제작':
        producers.append(cast)
      elif cast['role'] in [u'극본', u'각본']:
        writers.append(cast)
      else:
        roles.append(cast)
  except Exception, e:
    Log.Debug(repr(e))
    pass

  if roles:
    metadata.roles.clear()
    for role in roles:
      meta_role = metadata.roles.new()
      if 'role' in role:
        meta_role.role = role['role']
      if 'name' in role:
        meta_role.name = role['name']
      if 'photo' in role:
        meta_role.photo = role['photo']

  # (3) from photo page
  url_tmpl = DAUM_TV_PHOTO
  data = JSON.ObjectFromURL(url=url_tmpl % metadata.id)
  max_poster = int(Prefs['max_num_posters'])
  max_art = int(Prefs['max_num_arts'])
  idx_poster = 0
  idx_art = 0
  for item in data['data']:
    if item['photoCategory'] == '1' and idx_poster < max_poster:
      art_url = item['fullname']
      if not art_url: continue
      #art_url = RE_PHOTO_SIZE.sub("/image/", art_url)
      idx_poster += 1
      try: metadata.posters[art_url] = Proxy.Preview(HTTP.Request(item['thumbnail']), sort_order = idx_poster)
      #try: metadata.posters[art_url] = Proxy.Preview(HTTP.Request(item['thumbnail'], None, { 'Referer': url_tmpl }), sort_order = idx_poster)
      except: pass
    elif item['photoCategory'] in ['2', '50'] and idx_art < max_art:
      art_url = item['fullname']
      if not art_url: continue
      #art_url = RE_PHOTO_SIZE.sub("/image/", art_url)
      idx_art += 1
      try: metadata.art[art_url] = Proxy.Preview(HTTP.Request(item['thumbnail']), sort_order = idx_art)
      #try: metadata.art[art_url] = Proxy.Preview(HTTP.Request(item['thumbnail'], None, { 'Referer': url_tmpl }), sort_order = idx_art)
      except: pass
  Log.Debug('Total %d posters, %d artworks' %(idx_poster, idx_art))
  if idx_poster == 0:
    if poster_url:
      poster = HTTP.Request( poster_url )
      try: metadata.posters[poster_url] = Proxy.Media(poster)
      except: pass
    # else:
    #   url = 'http://m.movie.daum.net/m/tv/main?tvProgramId=%s' % metadata.id
    #   html = HTML.ElementFromURL( url )
    #   arts = html.xpath('//img[@class="thumb_program"]')
    #   for art in arts:
    #     art_url = art.attrib['src']
    #     if not art_url: continue
    #     art = HTTP.Request( art_url )
    #     idx_poster += 1
    #     metadata.posters[art_url] = Proxy.Preview(art, sort_order = idx_poster)

  # (4) from episode page
  page = HTTP.Request(DAUM_TV_EPISODE % metadata.id).content
  match = Regex('MoreView\.init\(\d+, (\[.*?\])\);', Regex.DOTALL).search(page)
  if match:
    data = JSON.ObjectFromString(match.group(1), max_size = JSON_MAX_SIZE)
    for item in data:
      episode_num = item['name']
      if not episode_num: continue
      episode = metadata.seasons['1'].episodes[int(episode_num)]
      episode.title = item['title']
      episode.summary = item['introduceDescription'].replace('\r\n', '\n').strip()
      if item['channels'][0]['broadcastDate']:
        episode.originally_available_at = Datetime.ParseDate(item['channels'][0]['broadcastDate'], '%Y%m%d').date()
      try: episode.rating = float(item['rate'])
      except: pass
      if directors:
        episode.directors.clear()
        for director in directors:
          meta_director = episode.directors.new()
          if 'name' in director:
            meta_director.name = director['name']
          if 'photo' in director:
            meta_director.photo = director['photo']
      if writers:
        episode.writers.clear()
        for writer in writers:
          meta_writer = episode.writers.new()
          if 'name' in writer:
            meta_writer.name = writer['name']
          if 'photo' in writer:
            meta_writer.photo = writer['photo']

    # (5) fill missing info
    # if Prefs['override_tv_id'] != 'None':
    #   page = HTTP.Request(DAUM_TV_DETAIL2 % metadata.id).content
    #   match = Regex('<em class="title_AKA"> *<span class="eng">([^<]*)</span>').search(page)
    #   if match:
    #     metadata.original_title = match.group(1).strip()

####################################################################################################
class DaumMovieAgent(Agent.Movies):
  name = "Daum Movie"
  languages = [Locale.Language.Korean]
  primary_provider = True
  accepts_from = ['com.plexapp.agents.localmedia']

  def search(self, results, media, lang, manual=False):
    return searchDaumMovie(results, media, lang)

  def update(self, metadata, media, lang):
    Log.Info("in update ID = %s" % metadata.id)
    updateDaumMovie(metadata)

    # override metadata ID
    if Prefs['override_movie_id'] != 'None':
      title = metadata.original_title if metadata.original_title else metadata.title
      if Prefs['override_movie_id'] == 'IMDB':
        url = IMDB_TITLE_SRCH % urllib.quote_plus("%s %d" % (title.encode('utf-8'), metadata.year))
        page = HTTP.Request( url ).content
        match = RE_IMDB_ID.search(page)
        if match:
          metadata.id = match.group(1)
          Log.Info("override with IMDB ID, %s" % metadata.id)

class DaumMovieTvAgent(Agent.TV_Shows):
  name = "Daum Movie"
  primary_provider = True
  languages = [Locale.Language.Korean]
  accepts_from = ['com.plexapp.agents.localmedia']

  def search(self, results, media, lang, manual=False):
    return searchDaumTV(results, media, lang)

  def update(self, metadata, media, lang):
    Log.Info("in update ID = %s" % metadata.id)
    updateDaumTV(metadata)

    # override metadata ID
    if Prefs['override_tv_id'] != 'None':
      title = metadata.original_title if metadata.original_title else metadata.title
      if Prefs['override_tv_id'] == 'TVDB':
        url = TVDB_TITLE_SRCH % urllib.quote_plus(title.encode('utf-8'))
        xml = XML.ElementFromURL( url )
        node = xml.xpath('/Data/Series/seriesid')
        if node:
          metadata.id = node[0].text
          Log.Info("override with TVDB ID, %s" % metadata.id)
