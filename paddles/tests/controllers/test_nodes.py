from paddles.tests import TestApp


class TestNodesController(TestApp):

    def test_get_node_root(self):
        response = self.app.get('/nodes/')
        assert response.status_int == 200

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
