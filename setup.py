# -*- coding: utf-8 -*-
try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

setup(
    name='paddles',
    version='0.1',
    description='',
    author='',
    author_email='',
    install_requires=[
        "pecan",
    ],
    test_suite='paddles',
    zip_safe=False,
    include_package_data=True,
    packages=find_packages(exclude=['ez_setup']),
    entry_points="""
        [pecan.command]
        populate=paddles.commands.populate:PopulateCommand
        reparse=paddles.commands.reparse:ReparseCommand
        dedupe=paddles.commands.dedupe:DedupeCommand
        delete=paddles.commands.delete:DeleteCommand
        expire_jobs=paddles.commands.expire_jobs:ExpireJobsCommand
        node_jobs=paddles.commands.node_jobs:NodeJobsCommand
        set_status=paddles.commands.set_status:SetStatusCommand
        set_targets=paddles.commands.set_targets:SetTargetsCommand
        import_nodes=paddles.commands.import_nodes:ImportNodesCommand
        queue_stats=paddles.commands.queue_stats:QueueStatsCommand
        node_stats=paddles.commands.node_stats:NodeStatsCommand
        """
)
