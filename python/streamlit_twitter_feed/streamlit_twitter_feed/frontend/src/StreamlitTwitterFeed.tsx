import {
  Streamlit,
  StreamlitComponentBase,
  withStreamlitConnection,
} from "streamlit-component-lib"
import React, { ReactNode } from "react"
import "./StreamlitTwitterFeed.css"

import { Avatar, styled } from "@material-ui/core";
import VerifiedUserIcon from "@material-ui/icons/VerifiedUser";
import ChatBubbleOutlineIcon from "@material-ui/icons/ChatBubbleOutline";
import RepeatIcon from "@material-ui/icons/Repeat";
import FavoriteBorderIcon from "@material-ui/icons/FavoriteBorder";
import PublishIcon from "@material-ui/icons/Publish";

interface State {
  numClicks: number
  isFocused: boolean
}

const StyledAvatar = styled(Avatar)({

});

/**
 * This is a React-based component template. The `render()` function is called
 * automatically when your component should be re-rendered.
 */

class StreamlitTwitterFeed extends StreamlitComponentBase<State> {
  public state = { numClicks: 0, isFocused: false }

  public render = (): ReactNode => {
    // taking from https://github.com/MertCankaya/Twitter-Clone/blob/main/src/Post.js
    const tweets = this.props.args["tweets"]
    const tweetsDsiplayed = tweets.map((tweet: any) =>
      <div className="post">
        <div className="post__avatar">
          <Avatar src={tweet["author.profile_image_url"]} />
        </div>
        <div className="post__body">
          <div className="post__header">
            <div className="post__headerText">
              <h3>
                {tweet["author.name"]}{" "}
                <span className="post__headerSpecial">
                  @{tweet["author.username"]}
                </span>
                <span>{tweet["created_at"]}</span>
              </h3>
            </div>
            <div className="post__headerDescription">
              <p>{tweet.text}</p>
            </div>
          </div>
          <img src={""} alt="" />
          <div className="post__footer">
            <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
              <ChatBubbleOutlineIcon fontSize="small" />
              <span className="post__headerSpecial">{tweet["public_metrics.reply_count"]}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
              <RepeatIcon fontSize="small" />
              <span className="post__headerSpecial">{tweet["public_metrics.retweet_count"]}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
              <FavoriteBorderIcon fontSize="small" />
              <span className="post__headerSpecial">{tweet["public_metrics.reply_count"]}</span>
            </div>
            <a href={tweet["tweet_link"]} target="_blank">
              <PublishIcon fontSize="small" />
            </a>
          </div>
        </div >
      </div >
    )
    return (
      <div className="container">
        {tweetsDsiplayed}
      </div>
    )
  }

  /** Click handler for our "Click Me!" button. */
  private onClicked = (): void => {
    // Increment state.numClicks, and pass the new value back to
    // Streamlit via `Streamlit.setComponentValue`.
    this.setState(
      prevState => ({ numClicks: prevState.numClicks + 1 }),
      () => Streamlit.setComponentValue(this.state.numClicks)
    )
  }

  /** Focus handler for our "Click Me!" button. */
  private _onFocus = (): void => {
    this.setState({ isFocused: true })
  }

  /** Blur handler for our "Click Me!" button. */
  private _onBlur = (): void => {
    this.setState({ isFocused: false })
  }
}

// "withStreamlitConnection" is a wrapper function. It bootstraps the
// connection between your component and the Streamlit app, and handles
// passing arguments from Python -> Component.
//
// You don't need to edit withStreamlitConnection (but you're welcome to!).
export default withStreamlitConnection(StreamlitTwitterFeed)
