class AddressFilter(object):
    def __init__(self):
        # Ignore and accept are mutually exclusive for 'rcpt' filter
        self._ignore_rcpt = set()
        self._accept_rcpt = set()
        
        # Ignore and accept are mutually exclusive for 'from' filter
        self._ignore_from = set()
        self._accept_from = set()
        
        # Used to manage, using contexts, mutually exclusive filters and set filter parameters.
        self._filters =\
            {
                # Context
                'rcpt' :
                    {
                        '_using' : None,
                        '__using_validator' : (lambda value: value in (None, 'ignore', 'accept')),
                        'ignore' : (AddressFilter._ignore_rcpt_filter, (self._ignore_rcpt,)),
                        'accept' : (AddressFilter._accept_rcpt_filter, (self._accept_rcpt,)),
                    },
                'from' :
                    {
                        '_using' : None,
                        '__using_validator' : (lambda value: value in (None, 'ignore', 'accept')),
                        'ignore' : (AddressFilter._ignore_from_filter, (self._ignore_from,)),
                        'accept' : (AddressFilter._accept_from_filter, (self._accept_from,)),
                    },
            }
        
    def __call__(self, mail):
        for conf in self._filters.itervalues():
            using = conf.get('_using')
            if using is not None:
                func, args = conf[using]
                mail = func(mail, *args)
        return mail
        
    def _get_context_conf(self, ctx):
        conf = self._filters.get(ctx)
        
        if conf is None:
            raise ValueError('context "{0}" not found'.format(ctx))
        
        return conf
        
    def _assert_conf_has_option_and_get_name(self, conf, option):
        _option = '_{0}'.format(option)
        
        if _option not in conf:
            raise ValueError('invalid option "{0}"'.format(option))
            
        return _option
        
    def _set_context_option(self, ctx, option, value):
        conf = self._get_context_conf(ctx)
        _option = self._assert_conf_has_option_and_get_name(conf, option)
        
        option_validator = conf.get('__{0}_validator'.format(option))

        if (option_validator is not None) and (not option_validator(value)):
            raise ValueError('invalid value "{0}" for option "{1}"'.format(value, option))
        
        conf[_option] = value
        
    def _get_context_option(self, ctx, option):
        conf = self._get_context_conf(ctx)
        _option = self._assert_conf_has_option_and_get_name(conf, option)
        return conf[_option]
        
    def _get_filter(self, ctx, filter_name):
        conf = self._get_context_conf(ctx)
        
        if filter_name.startswith('_'):
            raise ValueError('filter name cannot start with "_"')
            
        filter_pair = conf.get(filter_name)
        
        if filter_pair is None:
            raise ValueError('filter "{0}" not found in context "{1}"'.format(filter_name, ctx))
            
        return filter_pair
        
    # /----------------------------- public api ----------------------------------------------\
    
    def clear(self, ctx, filter_name):
        _, args  = self._get_filter(ctx, filter_name)
        args[0].clear()
        
    def use(self, ctx, filter_name):
        self._set_context_option(ctx, 'using', filter_name)
    
    def update(self, ctx, filter_name, addresses):
        _, args  = self._get_filter(ctx, filter_name)
        args[0].update(addresses)
        
    def reset(self):
        for ctx, conf in self._filters.iteritems():
            self._set_context_option(ctx, 'using', None)
            
            for k, v in conf.iteritems():
                if not k.startswith('_'):
                    v[1][0].clear()

    def get_state(self):
        state = {}
        
        for ctx, conf in self._filters.iteritems():
            data = {}
            for k, v in conf.iteritems():
                if not k.startswith('__'):
                    if k.startswith('_'):
                        data[k[1:]] = v
                    else:
                        data[k] = list(v[1][0])

            state[ctx] = data
        
        return state

    # \---------------------------------------------------------------------------------------/
        
    @staticmethod
    def _ignore_rcpt_filter(mail, rcpts):
        if (set(mail.rcpttos) - rcpts):
            return mail

    @staticmethod
    def _accept_rcpt_filter(mail, rcpts):
        if (not rcpts) or (set(mail.rcpttos).intersection(rcpts)):
            return mail

    @staticmethod
    def _ignore_from_filter(mail, froms):
        if mail.mailfrom not in froms:
            return mail

    @staticmethod
    def _accept_from_filter(mail, froms):
        if (not froms) or (mail.mailfrom in froms):
            return mail
