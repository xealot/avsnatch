#!/usr/bin/python
from datetime import datetime
from blessings import Terminal
from scheduler import ESTATE_WANTED, ESTATE_SKIPPED, EPISODE_STATES
from scheduler.storage import get_session, Series, Episode
from scripts import BaseScript, SubCommand
from sourcedb import load_info_source


class SeriesCommand(SubCommand):
    def sub_commands(self):
        return {
            'add': AddCommand,
            'list': ListCommand,
            'episodes': EpisodesCommand,
            'episode': EpisodeCommand
        }


class ListCommand(BaseScript):
    def start(self, args, config):
        term = Terminal()
        session = get_session()

        # Lookup local series info.
        shows = session.query(Series).all()

        for show in shows:
            print '- {s.tvdb_id}: {s.name} {s.airday} at {s.airtime} on {s.network} and is {t.green}{s.status}{t.normal}'.format(t=term, s=show)


class AddCommand(BaseScript):
    def configure_args(self, parser):
        super(AddCommand, self).configure_args(parser)
        parser.add_argument('series_id', help="The TVDB Id of the series to add.")
        parser.add_argument('--unaired-state', dest="unaired", default="", help="Set the shows that have no aired yet to one of the following: skipped, ignored, wanted")

    def start(self, args, config):
        #:TODO: Move this logic into the CORE so it can be used via library access.
        today = datetime.today()
        session = get_session()

        # Lookup Series Information
        tv = load_info_source('tv', config['TVDB_API_KEY'])
        series = tv.get_series(args.series_id)
        episodes = series.pop('episodes')

        # Add series and episode data to database.
        series = Series(**series)
        session.merge(series)

        for e in episodes:
            episode = Episode(**e)
            episode.state = ESTATE_SKIPPED if episode.air_date < today else ESTATE_WANTED
            session.merge(episode)

        session.commit()

        print 'The series, "{}" has been added/updated along with {} episodes.'.format(series.name, len(episodes))


class EpisodesCommand(BaseScript):
    def configure_args(self, parser):
        super(EpisodesCommand, self).configure_args(parser)
        group = parser.add_mutually_exclusive_group(required=False)
        group.add_argument('--wanted', dest='state', action="store_const", const='wanted', help="Only show wanted episodes.")
        group.add_argument('--searching', dest='state', action="store_const", const='searching', help="Only show searching episodes")
        parser.add_argument('series_id', help="The TVDB Id of the series to add.")

    def start(self, args, config):
        #:TODO: Move this logic into the CORE so it can be used via library access.
        session = get_session()

        # Lookup local series info.
        series = session.query(Series).filter_by(tvdb_id=args.series_id).first()

        for episode in series.episodes:
            print ' - {e.id}: S{e.season:02d}E{e.episode:02d} {e.air_date} [{e.state:^10s}] > {e.name}'.format(e=episode)


class EpisodeCommand(BaseScript):
    def configure_args(self, parser):
        super(EpisodeCommand, self).configure_args(parser)
        parser.add_argument('--state', dest='state', nargs='?', help="Set episode state.")
        parser.add_argument('episode_id', help="The Id of the episode.")

    def start(self, args, config):
        #:TODO: Move this logic into the CORE so it can be used via library access.
        session = get_session()

        episode = session.query(Episode).filter_by(id=args.episode_id).first()
        print 'Episode {e.id}: S{e.season:02d}E{e.episode:02d} {e.air_date} [{e.state:^10s}] > {e.name}'.format(e=episode)

        if args.state and args.state in EPISODE_STATES:
            episode.state = args.state
            session.commit()
            print 'Updated episode state to: {}'.format(args.state)





if '__main__' == __name__:
    print 'Run this Utility from the "tv" command.'
