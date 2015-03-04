# Build roster from input file
#
# Created by Darrin Speegle
# Updates by Paul Rebillot, 03/2015
#
# File format (roster.in):
#
# Name (nickname)\tGender\tAbility or Name\tGender\tAbility
# Name1 : Name2   -- preferred on same team
# Name1 = Name2   -- on same team
# Name1 ! Name 2  -- absolutely not on same team
# Name  -- Teamname        -- a manager
#
import random
import commands

typeLabel = ['Move one player', 'Trade two players', 'Two for one trade', 'Three way trade', 'Two for two trade', 'Three for three trade', 'Three way trade of two players', 'Three way trade of two players (opposite directions)']

class Roster:
  def __init__(self, filename):
    # Constraints:
    self._numTeams = 12
    self._minWomen = 6
    self._minMen = 12
    self._minTeamSize = 18
    self._maxTeamSize = 19
    self._totalThresh = .1  # Best team can't have more then 10% total ratings than worst
    self._sevenThresh = .1

    # Load the data
    self._nameLookup = list()
    self._idLookup = dict()
    self._fullNameLookup = list()
    self._genderLookup = list() # Id to M/F
    self._abilityLookup = list() # To to score
    self._baggage = list() # Of pairs of ids
    self._baggageLookup = list() # Player to set
    self._forced = list() # Of sets
    self._conflict = list() # Of sets
    self._managers = dict() # id -> team name

    lines = (''.join(file(filename)).replace('\r','\n')).split('\n')
    self._numPlayers = 0
    for l in lines:
      l = l.strip()
      if l.startswith('numTeams'):
        self._numTeams = int(l.split()[1])
      elif l.startswith('minWomen'):
        self._minWomen = int(l.split()[1])
      elif l.startswith('minMen'):
        self._minMen = int(l.split()[1])
      elif l.startswith('minTeamSize'):
        self._minTeamSize = int(l.split()[1])
      elif l.startswith('maxTeamSize'):
        self._maxTeamSize = int(l.split()[1])
      elif l.count('\t') == 2: #temp change from 3 to 2
        name = l.split('\t')[0].strip()
        self._fullNameLookup.append(name)
        if '(' in name:
          name = name.split('(')[0].strip()
        self._nameLookup.append(name)
        self._idLookup[name] = self._numPlayers
        self._numPlayers += 1
        if 'f' not in l.split('\t')[1].lower():#temp change from 3 to 1
          self._genderLookup.append('M')
        else:
          self._genderLookup.append('F')
        self._abilityLookup.append(int(l.split('\t')[2]))
      elif ':' in l:  # Baggage
        try:
          self._baggage.append( (self._idLookup[l.split(':')[0].strip()], self._idLookup[l.split(':')[1].strip()]) )
        except:
          print 'Invalid baggage', l
      elif '=' in l:  # Forced baggage
        try:
          self._forced.append( (self._idLookup[l.split('=')[0].strip()], self._idLookup[l.split('=')[1].strip()]) )
        except:
          print 'Invalid forcing', l
      elif '!' in l:  # Forced baggage
        try:
          self._conflict.append( (self._idLookup[l.split('!')[0].strip()], self._idLookup[l.split('!')[1].strip()]) )
        except:
          print 'Invalid conflict', l
      elif '--' in l:  # Manager
        self._managers[self._idLookup[l.split('--')[0].strip()]] = l.split('--')[1].strip()
      else:
        print l

    # Build lookup of baggage
    for i in range(self._numPlayers):
      self._baggageLookup.append(list())
    for b in self._baggage:
      self._baggageLookup[b[0]].append(b[1])
    self._baggageLookup = [ set(x) for x in self._baggageLookup ]

    # Stored data
    self._rosterValues = dict() # tuple of tuples -> tuple
    self._savedRosters = dict() # String to roster (tuple of tuples)
    self._currentRoster = self.randomRoster()
    self._bestRoster = self._currentRoster

    self._bestV = None
    self._bsetR = None

  def randomRoster(self):
    r = list()
    for i in range(self._numTeams):
      r.append(list())
    for i in range(self._numPlayers):

      r[random.randint(0, self._numTeams-1)].append(i)
    return tuple([ tuple(t) for t in r ])

  def rosterValue(self, r):
    # Tuple:  ( total of shortage of men on teams,
    #           total of shortage of women on teams,
    #           total error in team sizes,
    #           number of excess managers on teams,
    #           number of forced baggage ignored,
    #           number of conflicts ignored,
    #           max percent difference in total ratings if over threshold or zero,
    #           max percent different in seven best ratings if over threshold or zero,
    #           number people with multiple baggage requests but getting none,
    #           number of people with mutual baggage and no other ignored,
    #           number of baggage conflicts,
	#			max percent difference in total women's ratings
	#			max percent difference in total men's ratings
    #           larger of the next two numbers,
    #           max percent difference in total ratings,
    #           max percent difference in seven best ratings )
	menShort = 0
	womenShort = 0
	teamSizeError = 0
	extraManagers = 0
	forcedBad = 0
	conflictsBad = 0
	nobaggage = 0
	noMutualBaggage = 0
	baggageBad = 0
	totals = []
	sevens = []
	mtotals = []
	wtotals = []

	teams = [0] * self._numPlayers
	i = 0
	for t in r:
		for p in t:
			teams[p] = i
		i += 1

    # Team totals, etc.
	for t in r:
		men = 0
		women = 0
		managers = 0
		menTotalTemp = 0
		womenTotalTemp = 0
		scores = []

		if len(t) < self._minTeamSize:
			teamSizeError += self._minTeamSize - len(t)
		elif len(t) > self._maxTeamSize:
			teamSizeError += len(t) - self._minTeamSize


		for p in t:
			if self._genderLookup[p] == 'M':
				men += 1
				menTotalTemp += self._abilityLookup[p]
			else:
				women += 1
				womenTotalTemp += self._abilityLookup[p]
			if self._managers.has_key(p):
				managers += 1
			scores.append(self._abilityLookup[p])

		scores.sort()
		scores.reverse()
		totals.append(sum(scores))
		sevens.append(sum(scores[:7]))
		mtotals.append(menTotalTemp)
		wtotals.append(womenTotalTemp)

		if men < self._minMen:
			menShort += self._minMen - men
		if women < self._minWomen:
			womenShort += self._minWomen - women
		if managers > 1:
			extraManagers += managers-1

    # Baggage
	for b in self._baggage:
		if teams[b[0]] != teams[b[1]]:
			baggageBad += 1
	for b in self._forced:
		if teams[b[0]] != teams[b[1]]:
			forcedBad += 1
	for b in self._conflict:
		if teams[b[0]] == teams[b[1]]:
			conflictsBad += 1

	# Not getting baggage
	for i in range(self._numPlayers):
		if len(self._baggageLookup[i]) > 1:
			someone = False
			for p in self._baggageLookup[i]:
				if teams[i] == teams[p]:
					someone = True
			if not someone:
				nobaggage += 1

    # Mutual baggageBad
	for i in range(self._numPlayers):
		if len(self._baggageLookup[i]) == 1:
			other = list(self._baggageLookup[i])[0]
			if len(self._baggageLookup[other]) == 1 and i in self._baggageLookup[other] and teams[other] != teams[i]:
				noMutualBaggage += 1

	totalPerc = float(max(totals))/min(totals) - 1
	sevenPerc = float(max(sevens))/min(sevens) - 1
	mtotalPerc = float(max(mtotals))/min(mtotals) - 1
	wtotalPerc = float(max(wtotals))/min(wtotals) - 1

	return (menShort, womenShort, teamSizeError, extraManagers, forcedBad, conflictsBad, max(self._totalThresh, totalPerc), max(self._sevenThresh, sevenPerc), nobaggage, noMutualBaggage, baggageBad, wtotalPerc, mtotalPerc, max(totalPerc, sevenPerc), totalPerc, sevenPerc)

  def neighbors(self, r, s):
    teams = [0] * self._numPlayers
    i = 0
    for t in r:
      for p in t:
        teams[p] = i
      i += 1

    if s == 0:
      # Move a single person
      for i in range(self._numPlayers):
        for j in range(self._numTeams):
          if j != teams[i]:
            r2 = [ list(t) for t in r ]
            r2[teams[i]].remove(i)
            r2[j].append(i)

            r2 = tuple( [ tuple(t) for t in r2 ] )

            yield r2

    elif s == 1:
      # Swap two
      for i in range(self._numPlayers):
        for j in range(i+1,self._numPlayers):
          if teams[i] != teams[j]:
            r2 = [ list(t) for t in r ]
            r2[teams[i]].remove(i)
            r2[teams[j]].remove(j)
            r2[teams[j]].append(i)
            r2[teams[i]].append(j)

            r2 = tuple( [ tuple(t) for t in r2 ] )

            yield r2

    elif s == 2:
      # Two for one
      for t1 in range(self._numTeams):
        for t2 in range(self._numTeams):
          if t1 != t2:
            for i in r[t1]:
              for j in r[t1]:
                if i > j:
                  for k in r[t2]:
                    r2 = [ list(t) for t in r ]

                    r2[t1].remove(i)
                    r2[t1].remove(j)
                    r2[t2].remove(k)
                    r2[t1].append(k)
                    r2[t2].append(i)
                    r2[t2].append(j)

                    r2 = tuple( [ tuple(t) for t in r2 ] )

                    yield r2

    elif s == 3:
      # Three way trade
      for t1 in range(self._numTeams):
        for t2 in range(t1+1, self._numTeams):
          for t3 in range(t2+1, self._numTeams):
            for i in r[t1]:
              for j in r[t2]:
                for k in r[t3]:
                  r2 = [ list(t) for t in r ]

                  r2[t1].remove(i)
                  r2[t2].remove(j)
                  r2[t3].remove(k)

                  r2[t1].append(k)
                  r2[t2].append(i)
                  r2[t3].append(j)

                  r2 = tuple( [ tuple(t) for t in r2 ] )

                  yield r2

    elif s == 4:
      # Two for two trade
      for t1 in range(self._numTeams):
        for t2 in range(t1+1, self._numTeams):
          for i in r[t1]:
            for j in r[t1]:
              if i > j:
                for k in r[t2]:
                  for l in r[t2]:
                    if k > l:
                      r2 = [ list(t) for t in r ]

                      r2[t1].remove(i)
                      r2[t1].remove(j)
                      r2[t2].remove(k)
                      r2[t2].remove(l)

                      r2[t1].append(k)
                      r2[t1].append(l)
                      r2[t2].append(i)
                      r2[t2].append(j)

                      r2 = tuple( [ tuple(t) for t in r2 ] )
                      yield r2

    elif s == 5:
      # Three for three trade
      for t1 in range(self._numTeams):
        for t2 in range(t1+1, self._numTeams):
          for i in r[t1]:
            for j in r[t1]:
              if i > j:
                for k in r[t1]:
                  if j > k:
                    for l in r[t2]:
                      for m in r[t2]:
                        if l > m:
                          for n in r[t2]:
                            if m > n:
                              r2 = [ list(t) for t in r ]

                              r2[t1].remove(i)
                              r2[t1].remove(j)
                              r2[t1].remove(k)
                              r2[t2].remove(l)
                              r2[t2].remove(m)
                              r2[t2].remove(n)

                              r2[t1].append(l)
                              r2[t1].append(m)
                              r2[t1].append(n)
                              r2[t2].append(i)
                              r2[t2].append(j)
                              r2[t2].append(k)

                              r2 = tuple( [ tuple(t) for t in r2 ] )
                              yield r2

    elif s == 6:
      # Three way trade of two players
      for t1 in range(self._numTeams):
        for t2 in range(t1+1, self._numTeams):
          for t3 in range(t2+1, self._numTeams):
            for i in r[t1]:
              for i2 in r[t1]:
                if i2 > i:
                  for j in r[t2]:
                    for j2 in r[t2]:
                      if j2 > j:
                        for k in r[t3]:
                          for k2 in r[t3]:
                            if k2 > k:
                              r2 = [ list(t) for t in r ]

                              r2[t1].remove(i)
                              r2[t2].remove(j)
                              r2[t3].remove(k)
                              r2[t1].remove(i2)
                              r2[t2].remove(j2)
                              r2[t3].remove(k2)

                              r2[t1].append(k)
                              r2[t2].append(i)
                              r2[t3].append(j)
                              r2[t1].append(k2)
                              r2[t2].append(i2)
                              r2[t3].append(j2)

                              r2 = tuple( [ tuple(t) for t in r2 ] )

                              yield r2


    elif s == 7:
      # Three way trade of two players but opposite directions
      for t1 in range(self._numTeams):
        for t2 in range(t1+1, self._numTeams):
          for t3 in range(t2+1, self._numTeams):
            for i in r[t1]:
              for i2 in r[t1]:
                if i2 > i:
                  for j in r[t2]:
                    for j2 in r[t2]:
                      if j2 > j:
                        for k in r[t3]:
                          for k2 in r[t3]:
                            if k2 > k:
                              r2 = [ list(t) for t in r ]

                              r2[t1].remove(i)
                              r2[t2].remove(j)
                              r2[t3].remove(k)
                              r2[t1].remove(i2)
                              r2[t2].remove(j2)
                              r2[t3].remove(k2)

                              r2[t1].append(k)
                              r2[t2].append(i)
                              r2[t3].append(j)
                              r2[t1].append(j2)
                              r2[t2].append(k2)
                              r2[t3].append(i2)

                              r2 = tuple( [ tuple(t) for t in r2 ] )

                              yield r2


  def hillClimb(self, r=None):
    if not r:
      r = self.randomRoster()

    v = self.rosterValue(r)
    bestV = v
    bestR = r

    if not self._bestV:
      self._bestV = bestV
      self._bestR = bestR

    changed = True
    while changed:
      changed = False
      for t in range(8):
        ngh = self.neighbors(bestR, t)
        print 'Considering type %d: %s' % (t, typeLabel[t])
        count = 0
        #random.shuffle(ngh)
        for n in ngh:
			count += 1
			if count % 10000 == 0:
				print count, bestV
			v = self.rosterValue(n)
			if v < bestV:
				bestV = v
				bestR = n
				changed = True

				if bestV < self._bestV:
					self._bestV = bestV
					self._bestR = bestR

					print 'Best improved to', v
					#print bestR
			  
					self.printRoster(bestR,True,'roster.txt')

#				elif bestV[13] < 0.025:
#					print 'breaking because < 2.5%'
#					break
				else:
					#print 'Improved to', v
					pass

				break # One bet is good enough (we've randomly choosen which)
			elif v[15] < 0.025:
				print 'breaking because < 2.5%'
				break
			elif bestV[15] < 0.04 and count > 1000000:
				print 'breaking because < 4% and many counts'
				break
			

        if changed: # Don't move to more complicated neighbors yet
          break

    return bestR

  def printRoster(self, r, verbose=False, filename=None):
	i = 1

	if filename:
	  outFile = file(filename, 'w')

	for t in r:
		name = 'Team %i' % i
		m = 0
		f = 0
		abilities = []
		menAbilities = []
		womenAbilities = []
		i += 1
		roster = []
		for p in t:
			if verbose:
				missingBaggage = []
				for b in self._baggage:
					if b[0] == p:
						if b[1] not in t:
							missingBaggage.append(self._nameLookup[b[1]])
				roster.append('%3i) ' % p + self._nameLookup[p].ljust(30) + '%s %3i \t%s' % (self._genderLookup[p], self._abilityLookup[p], '; '.join(missingBaggage)))

				if len(self._baggageLookup[p]) == 1:
					other = list(self._baggageLookup[p])[0]
					if len(self._baggageLookup[other]) == 1 and p in self._baggageLookup[other] and other not in t:
						roster[-1] = roster[-1] + ' Mutual: ' + self._nameLookup[other]

				if self._genderLookup[p] == 'M':
					m += 1
					menAbilities.append(self._abilityLookup[p])
				else:
					f += 1
					womenAbilities.append(self._abilityLookup[p])
				abilities.append(self._abilityLookup[p])
			else:
				roster.append(self._nameLookup[p])
			try:
				name = self._managers[p]
			except:
				pass

		if filename:
			outFile.write(name)
			outFile.write('\n')
			outFile.write('-'*len(name))
			outFile.write('\n')
			if verbose:
				abilities.sort()
				abilities.reverse()
				outFile.write('M/F %d %d' % (m, f))
				outFile.write('\n')
				outFile.write('Total %d' % sum(abilities))
				outFile.write('\n')
				outFile.write('Seven %d' % sum(abilities[:7]))
				outFile.write('\n')
				outFile.write('MenTotal %d' % sum(menAbilities))
				outFile.write('\n')
				outFile.write('WomenTotal %d' % sum(womenAbilities))
				outFile.write('\n')
				outFile.write('\n')
			roster.sort()
			outFile.write('\n'.join(roster))
			outFile.write('\n')
			outFile.write('\n')
		else:
			print name
			print '-'*len(name)
			if verbose:
				abilities.sort()
				abilities.reverse()
				print 'M/F', m, f
				print 'Total', sum(abilities)
				print 'Seven', sum(abilities[:7])
				print 'MenTotal', sum(menAbilities)
				print 'WomenTotal', sum(womenAbilities)
				print
			roster.sort()
			print '\n'.join(roster)
			print

	if filename:
		outFile.close()

  def graphRoster(self, r, verbose=False, fname='roster'):
    ofile = file(fname+'.dot','w')

    ofile.write('digraph %s {\n' % fname)
    ofile.write('ratio=1;\n')
    ofile.write('overlap=false;\n')
    #ofile.write('splines=true;\n')
    i = 0
    bagNum = 0
    for t in r:
      i += 1
      name = 'Team %i' % i
      m = 0
      f = 0
      abilities = []
      roster = []
      for p in t:
        if verbose:
          roster.append('%i) ' % p + self._nameLookup[p] + ' %s %3i' % (self._genderLookup[p], self._abilityLookup[p]))
          if self._genderLookup[p] == 'M':
            m += 1
          else:
            f += 1
          abilities.append(self._abilityLookup[p])
        else:
          roster.append(self._nameLookup[p])
        try:
          name = self._managers[p]
        except:
          pass

        # Put player in graph
        ofile.write('Player%i [label="%s"];\n' % (p, roster[-1]))

      if verbose:
        abilities.sort()
        abilities.reverse()
        ofile.write('subgraph cluster%i {\n' % i)
        ofile.write('Team%i [shape=square,label="%s\\nM/F %i %i\\nTotal %i\\nSeven %i"];\n' % (i,name,m,f,sum(abilities),sum(abilities[:7])))
      else:
        ofile.write('Team%i [shape=square,label="Team %i"];\n' % (i,i))

      for p in t:
        ofile.write('Player%i;\n' % p)

      color = ['red','blue','darkgreen','purple','cyan','lawngreen','brown','yellow']
      for p in t:
        ofile.write('Team%i -> Player%i [color="%s",weight=0,style="invis"];\n' % (i,p,color[i-1]))

      ofile.write('}\n')

    #Put in baggage links, etc.
    for b in self._baggage:
      x = [ i for i in range(self._numTeams) if b[0] in r[i] and b[1] in r[i] ]
      if len(x) == 1:
        ofile.write('Player%i -> Player%i [weight=0, color="%s"];\n' % (b[0],b[1],color[x[0]]))
      else:
        ofile.write('Player%i -> Player%i [weight=0];\n' % (b[0],b[1]))
      bagNum += 1


    ofile.write('}\n')
    ofile.close()

    #print commands.getoutput('dot %s.dot -Teps -o %s.eps' % (fname, fname))

r = Roster('roster.in')
t = r.randomRoster()
print(r._numPlayers)
print(r._numTeams)


#t = ((102, 39, 87, 74, 120, 129, 130, 123, 40, 133, 13, 73, 67, 82, 58, 46, 19, 96), (89, 60, 54, 53, 116, 127, 37, 65, 81, 110, 32, 31, 48, 109, 4, 6, 118, 28), (101, 16, 68, 94, 125, 115, 34, 35, 56, 42, 142, 15, 88, 134, 105, 20, 98, 85), (93, 114, 3, 2, 91, 90, 136, 126, 12, 9, 51, 69, 36, 5, 131, 14, 121, 52), (29, 30, 111, 80, 44, 11, 112, 143, 97, 117, 100, 63, 140, 45, 21, 66, 84, 18), (59, 75, 122, 132, 72, 78, 95, 124, 25, 79, 47, 7, 43, 108, 103, 135, 137, 83), (70, 139, 71, 138, 41, 106, 113, 119, 10, 24, 64, 23, 128, 92, 26, 17, 107, 8), (27, 55, 76, 61, 77, 38, 50, 49, 33, 99, 57, 22, 104, 62, 141, 86, 1, 0))

# if raw_input('Use existing roster? (y/n)')[0].lower() == 'y':
  # t = input('Enter roster\n')

# r.printRoster(t,True)
# #r.graphRoster(t,True)

# v = r.rosterValue(t)
# bestV = v
# bestT = t
# r.hillClimb(t)


# for i in range(100):
  # t = r.hillClimb()
  # v = r.rosterValue(t)

  # if v < bestV:
    # bestV = v
    # bestT = t

    # r.printRoster(t,True)
    # #r.graphRoster(t,True)
    # print 'r =', bestT

  # print
  # print i, v
  # print



