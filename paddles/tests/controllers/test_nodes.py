from paddles.tests import TestApp


class TestNodesController(TestApp):

    def test_get_node_root(self):
        response = self.app.get('/nodes/')
        assert response.status_int == 200

    def test_get_count(self):
        node_names = ['n1', 'n2', 'n3', 'n4', 'n5']
        nodes = [dict(name=n) for n in node_names]
        for node in nodes:
            response = self.app.post_json('/nodes/', node)
        response = self.app.get('/nodes/?count=3')
        assert len(response.json) == 3

    def test_job_creates_nodes(self):
        run_name = 'job_creates_nodes'
        job_id = 276
        target_names = ['t1', 't2', 't3']
        targets = {}
        for name in target_names:
            targets['u@' + name] = ''
        self.app.post_json('/runs/', dict(name=run_name))
        self.app.post_json('/runs/%s/jobs/' % run_name, dict(
            job_id=job_id,
            targets=targets,
        ))
        response = self.app.get('/runs/{name}/jobs/{id}/'.format(
            name=run_name, id=job_id))
        response = self.app.get('/nodes/')
        got_target_names = [node['name'] for node in response.json]
        assert sorted(got_target_names) == sorted(target_names)

    def test_job_stats(self):
        run_name = 'job_stats'
        job_ids = [1, 2, 3]
        target_names = ['t1', 't2']
        targets = {}
        for name in target_names:
            targets['u@' + name] = ''
        for job_id in job_ids:
            self.app.post_json('/runs/{name}/jobs/'.format(name=run_name),
                               dict(job_id=job_id, targets=targets,
                                    status='fail'))
        result = {}
        for name in target_names:
            result[name] = dict(fail=len(job_ids))
        response = self.app.get('/nodes/job_stats/')
        assert response.json == result

    def test_post(self):
        node_name = 'puppies'
        node_data = dict(name=node_name, locked=False)
        self.app.post_json('/nodes/', node_data)
        response = self.app.get('/nodes/{name}/'.format(name=node_name))
        assert response.json['name'] == node_name

    def test_multiple_machine_types(self):
        self.app.post_json('/nodes/', dict(name='node1', machine_type='type1'))
        self.app.post_json('/nodes/', dict(name='node2', machine_type='type2'))
        self.app.post_json('/nodes/', dict(name='node3', machine_type='type3'))
        self.app.post_json('/nodes/', dict(name='node4', machine_type='type4'))
        response = self.app.get('/nodes/?machine_type=type1|type2|type4')
        wanted_types = ['type1', 'type2', 'type4']
        got_types = sorted([n['machine_type'] for n in response.json])
        assert got_types == wanted_types

    def test_query_locked_by(self):
        self.app.post_json('/nodes/', dict(name='query_locked_by1',
                                           locked=True, locked_by='gal'))
        self.app.post_json('/nodes/', dict(name='query_locked_by2',
                                           locked=True, locked_by='gal'))
        self.app.put_json('/nodes/query_locked_by1/',
                          dict(locked=False, locked_by='gal'))
        self.app.put_json('/nodes/query_locked_by1/',
                          dict(locked=True, locked_by='guy'))
        response = self.app.get('/nodes/?locked_by=guy')
        assert response.json[-1]['name'] == 'query_locked_by1'

    def test_lock_many_simple(self):
        count = 2
        node_names = ('cat', 'dog', 'dragon')
        for name in node_names:
            self.app.post_json(
                '/nodes/',
                dict(name=name, machine_type='pet', locked=False, up=True,)
            )

        response = self.app.post_json(
            '/nodes/lock_many/',
            dict(count=count, machine_type='pet', description='desc',
                 locked_by='me')
        )
        assert len(response.json) == count

    def test_lock_many_multi(self):
        count = 5
        nodes = dict(
            munchkin='cat',
            tabby='cat',
            mainecoon='cat',
            corgi='dog',
            heeler='dog',
            husky='dog',
        )
        for (name, type_) in nodes.iteritems():
            self.app.post_json(
                '/nodes/',
                dict(name=name, machine_type=type_, locked=False, up=True,)
            )

        response = self.app.post_json(
            '/nodes/lock_many/',
            dict(count=count, machine_type='cat|dog', description='desc',
                 locked_by='me')
        )
        types = [node['machine_type'] for node in response.json]
        num_dogs = types.count('dog')
        num_cats = types.count('cat')
        assert num_dogs + num_cats == 5

    def test_lock_many_too_many(self):
        count = 4
        node_names = ('cat', 'dog', 'dragon')
        for name in node_names:
            self.app.post_json(
                '/nodes/',
                dict(name=name, machine_type='pet', locked=False, up=True,)
            )

        response = self.app.post_json(
            '/nodes/lock_many/',
            dict(count=count, machine_type='pet', description='desc',
                 locked_by='me'),
            expect_errors=True,
        )
        assert response.status_int == 503

    def test_lock_many_already_taken(self):
        count = 1
        node_names = ('cat', 'dog', 'dragon')
        for name in node_names:
            self.app.post_json(
                '/nodes/',
                dict(name=name, machine_type='pet', locked=True,
                     locked_by='you', up=True,)
            )

        response = self.app.post_json(
            '/nodes/lock_many/',
            dict(count=count, machine_type='pet', description='desc',
                 locked_by='me'),
            expect_errors=True,
        )
        assert response.status_int == 503

    def test_lock_many_recycle(self):
        count = 2
        node_names = ('cat', 'dog', 'dragon')
        desc = 'my_super_cool_test_run'
        locked_by = 'me'
        for name in node_names:
            self.app.post_json(
                '/nodes/',
                dict(name=name, machine_type='pet', locked=True,
                     locked_by=locked_by, description=desc, up=True,)
            )

        response = self.app.post_json(
            '/nodes/lock_many/',
            dict(count=count, machine_type='pet', description=desc,
                 locked_by=locked_by)
        )
        assert len(response.json) == count

    def test_unlock_many_simple(self):
        mtype = 'ulmtest'
        locked_by = 'unlock@many'
        desc = 'unlock_many'
        count = 7
        node_names = ['n%s' % i for i in range(count)]
        for name in node_names:
            self.app.post_json(
                '/nodes/',
                dict(name=name, machine_type=mtype, locked=True,
                     locked_by=locked_by, description=desc, up=True,)
            )

        response = self.app.post_json('/nodes/unlock_many/',
                                      dict(names=node_names,
                                           locked_by=locked_by))
        got_names = [node['name'] for node in response.json]
        assert sorted(got_names) == node_names
        got_locked = [node['locked'] for node in response.json]
        assert list(set(got_locked)) == [False]


class TestNodeController(TestApp):

    def test_get_nonexistent_node(self):
        response = self.app.get('/nodes/this_is_not_here/', expect_errors=True)
        assert response.status_int == 404

    def test_single_node_job_stats(self):
        run_name = 'job_stats'
        job_ids = [1, 2, 3]
        target_name = 't1'
        targets = {'u@' + target_name: ''}
        for job_id in job_ids:
            self.app.post_json('/runs/{name}/jobs/'.format(name=run_name),
                               dict(job_id=job_id, targets=targets,
                                    status='running'))

        result = {'running': len(job_ids), 'pass': 0, 'fail': 0, 'dead': 0,
                  'unknown': 0, 'queued': 0}
        response = self.app.get('/nodes/{node}/job_stats/'.format(
            node=target_name))
        assert response.json == result

    def test_update(self):
        node_name = 'kittens'
        self.app.post_json('/nodes/', dict(name=node_name, locked=False))
        self.app.put_json('/nodes/{name}/'.format(name=node_name),
                          dict(name=node_name, locked=True))
        response = self.app.get('/nodes/{name}/'.format(name=node_name))
        assert response.json['locked'] is True

    def test_check(self):
        node_name = 'crabs'
        self.app.post_json('/nodes/', dict(name=node_name, locked=False))
        response = self.app.get(
            '/nodes/{name}/lock'.format(name=node_name),
            dict(locked=True, locked_by='me'))
        assert response.json['locked'] is False

    def test_lock(self):
        node_name = 'kittens'
        self.app.post_json('/nodes/', dict(name=node_name, locked=False))
        response = self.app.put_json(
            '/nodes/{name}/lock'.format(name=node_name),
            dict(locked=True, locked_by='me'))
        assert response.json['locked'] is True and \
            response.json['locked_by'] == 'me'

    def test_lock_no_owner(self):
        node_name = 'kittens'
        self.app.post_json('/nodes/', dict(name=node_name, locked=False))
        response = self.app.put_json(
            '/nodes/{name}/lock'.format(name=node_name),
            dict(locked=True), expect_errors=True)
        assert response.status_int == 400

    def test_double_lock(self):
        node_name = 'kittens'
        self.app.post_json('/nodes/', dict(name=node_name, locked=True))
        response = self.app.put_json(
            '/nodes/{name}/lock'.format(name=node_name),
            dict(locked=True, locked_by='me'),
            expect_errors=True)
        assert response.status_int == 403

    def test_double_unlock(self):
        node_name = 'kittens'
        self.app.post_json('/nodes/', dict(name=node_name, locked=False))
        response = self.app.put_json(
            '/nodes/{name}/lock'.format(name=node_name),
            dict(locked=False, locked_by='me'),
            expect_errors=True)
        assert response.status_int == 400

    def test_unlock(self):
        node_name = 'ferrets'
        self.app.post_json('/nodes/',
                           dict(name=node_name, locked=True, locked_by='me'))
        response = self.app.put_json(
            '/nodes/{name}/lock'.format(name=node_name),
            dict(locked=False, locked_by='me'))
        assert response.json['locked'] is False and \
            response.json['locked_by'] is None

    def test_unlock_different_owner(self):
        node_name = 'minnows'
        self.app.post_json('/nodes/', dict(name=node_name, locked=True))
        response = self.app.put_json(
            '/nodes/{name}/lock'.format(name=node_name),
            dict(locked=False, locked_by='me'), expect_errors=True)
        assert response.status_int == 403

    def test_post_junk(self):
        response = self.app.post_json('/nodes/', dict(), expect_errors=True)
        assert response.status_int == 400

    def test_post_empty_name(self):
        response = self.app.post_json('/nodes/', dict(name=None),
                                      expect_errors=True)
        assert response.status_int == 400

    def test_post_dupe(self):
        node_dict = dict(name='post_me_twice')
        response = self.app.post_json('/nodes/', node_dict)
        response = self.app.post_json('/nodes/', node_dict, expect_errors=True)
        assert response.status_int == 400

    def test_update_nonexistent(self):
        node_name = 'missing_kitten'
        response = self.app.put_json('/nodes/{name}/'.format(name=node_name),
                                     dict(name=node_name, locked=True),
                                     expect_errors=True)
        assert response.status_int == 404

    def test_jobs_nonexistent(self):
        response = self.app.get('/nodes/missing_kitten/jobs/',
                                expect_errors=True)
        assert response.status_int == 404

    def test_job_stats_nonexistent(self):
        response = self.app.get('/nodes/missing_kitten/job_stats/',
                                expect_errors=True)
        assert response.status_int == 404
