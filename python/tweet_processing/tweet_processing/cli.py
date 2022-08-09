"""Console script for tweet_processing."""
import sys
import click


@click.command()
def main(args=None):
    """Console script for tweet_processing."""
    click.echo("Replace this message by putting your code into "
               "tweet_processing.cli.main")
    click.echo("See click documentation at https://click.palletsprojects.com/")
    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
