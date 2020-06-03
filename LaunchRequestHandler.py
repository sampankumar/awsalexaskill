import logging

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.utils import is_request_type, is_intent_name

from ask_sdk_core.dispatch_components import (
    AbstractRequestHandler, AbstractExceptionHandler,
    AbstractRequestInterceptor)


from ask_sdk_model import Response
from ask_sdk_model.interfaces.audioplayer import (
    PlayDirective, PlayBehavior, AudioItem, Stream)
from ask_sdk_core.handler_input import HandlerInput

from skill import (data, util)

import boto3

bucket_name = "samarthalexasongbucket"
prefix = "alexa/"


sb = SkillBuilder()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

index = 1

class CheckAudioInterfaceHandler(AbstractRequestHandler):
    """Check if device supports audio play.

    This can be used as the first handler to be checked, before invoking
    other handlers, thus making the skill respond to unsupported devices
    without doing much processing.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        if handler_input.request_envelope.context.system.device:
            # Since skill events won't have device information
            return handler_input.request_envelope.context.system.device.supported_interfaces.audio_player is None
        else:
            return False

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In CheckAudioInterfaceHandler")
        _ = handler_input.attributes_manager.request_attributes["_"]
        handler_input.response_builder.speak(
            _(data.DEVICE_NOT_SUPPORTED)).set_should_end_session(True)
        return handler_input.response_builder.response



class SkillEventHandler(AbstractRequestHandler):
    """Close session for skill events or when session ends.

    Handler to handle session end or skill events (SkillEnabled,
    SkillDisabled etc.)
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (handler_input.request_envelope.request.object_type.startswith(
            "AlexaSkillEvent") or
                is_request_type("SessionEndedRequest")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In SkillEventHandler")
        return handler_input.response_builder.response


class LaunchRequestHandler1(AbstractRequestHandler):
    """Handler for Skill Launch."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_request_type("LaunchRequest")(handler_input)

    # def handle(self, handler_input):
    #     # type: (HandlerInput) -> Response
    #     speech_text = "Welcome to the Alexa Skills Kit, you can say hello!"
    #
    #     handler_input.response_builder.speak(speech_text).ask(
    #         "Go ahead and say hello to me!").set_card(
    #         SimpleCard("Hello World", speech_text))
    #     return handler_input.response_builder.response

    def handle(self, handler_input):
        global index
        s3 = boto3.resource('s3')
        my_bucket = s3.Bucket(bucket_name)

        s3_result =  my_bucket.objects.filter(Prefix=prefix)
        print("s3_result %s" % (s3_result))

        for object_summary in s3_result:
            logger.info(object_summary.key)
            data.AUDIO_DATA.append(object_summary.key)

        #s3_conn  = client('s3')  # type: BaseClient  ## again assumes boto.cfg setup, assume AWS S3
        #s3_result =  s3_conn.list_objects_v2(Bucket=bucket_name, Prefix=prefix)

        util.play(data.AUDIO_DATA[index], "0", None , None, handler_input.response_builder)
        index = index + 1
        # for object_summary in s3_result:
        #     if "dhobi.mp3" in object_summary.key:
        #         util.play(object_summary.key, "0", None , None, handler_input.response_builder)
        return handler_input.response_builder.response


class PlaybackNearlyFinishedHandler(AbstractRequestHandler):
    """AudioPlayer.PlaybackNearlyFinished Directive received.

    Replacing queue with the URL again. This should not happen on live streams.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_request_type("AudioPlayer.PlaybackNearlyFinished")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In PlaybackNearlyFinishedHandler")
        logger.info("Playback nearly finished")
        logger.info(handler_input.request_envelope)
        logger.info(self)
        global index

        #request = handler_input.request_envelope.request
        if (len(data.AUDIO_DATA) > 0):
            logger.info("in s3 object list")
            util.play_later(data.AUDIO_DATA[index], 0, None, handler_input.response_builder)
            index = index + 1
        else:
            logger.info("in else")
            util.stop("Thanks for listening.", handler_input.response_builder)

        logger.info(handler_input.response_builder.response)
        return handler_input.response_builder.response


class HelpIntentHandler(AbstractRequestHandler):
    """Handler for providing help information to user."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In HelpIntentHandler")
        _ = handler_input.attributes_manager.request_attributes["_"]
        handler_input.response_builder.speak(
            _(data.HELP_MSG).format(
                util.audio_data(
                    handler_input.request_envelope.request)["card"]["title"])
        ).set_should_end_session(False)
        return handler_input.response_builder.response


class UnhandledIntentHandler(AbstractRequestHandler):
    """Handler for fallback intent, for unmatched utterances.

    2018-July-12: AMAZON.FallbackIntent is currently available in all
    English locales. This handler will not be triggered except in that
    locale, so it can be safely deployed for any locale. More info
    on the fallback intent can be found here:
    https://developer.amazon.com/docs/custom-skills/standard-built-in-intents.html#fallback
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In UnhandledIntentHandler")
        _ = handler_input.attributes_manager.request_attributes["_"]
        handler_input.response_builder.speak(
            _(data.UNHANDLED_MSG)).set_should_end_session(True)
        return handler_input.response_builder.response


class NextOrPreviousIntentHandler(AbstractRequestHandler):
    """Handler for next or previous intents."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (is_intent_name("AMAZON.NextIntent")(handler_input) or
                is_intent_name("AMAZON.PreviousIntent")(handler_input) or
                is_intent_name("AMAZON.RepeatIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In NextOrPreviousIntentHandler")
        #_ = handler_input.attributes_manager.request_attributes["_"]
        handler_input.response_builder.speak("Next")
        #_(data.CANNOT_SKIP_MSG)).set_should_end_session(True)
        return handler_input.response_builder.response


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Handler for cancel, stop or pause intents."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (is_intent_name("AMAZON.CancelIntent")(handler_input) or
                is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In CancelOrStopIntentHandler")
        #stopAttribute = handler_input.attributes_manager.request_attributes["_"]
        return util.stop("Goodbye.", handler_input.response_builder)


class PauseIntentHandler(AbstractRequestHandler):
    """Handler for cancel, stop or pause intents."""
    def can_handle(self, handler_input):
        return (handler_input.request_envelope.request.object_type == "IntentRequest"
                and handler_input.request_envelope.request.intent.name == "AMAZON.PauseIntent")

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In PauseIntentHandler")
        #stopAttribute = handler_input.attributes_manager.request_attributes["_"]
        return util.stop("Goodbye.", handler_input.response_builder)





class ResumeIntentHandler(AbstractRequestHandler):
    """Handler for resume intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("AMAZON.ResumeIntent")(handler_input)

    def handle(self, handler_input):
        handler_input.response_builder.add_directive(
            PlayDirective(
                play_behavior=PlayBehavior.REPLACE_ALL,
                audio_item=AudioItem(
                    stream=Stream(
                        token="https://samarthalexasongbucket.s3.eu-west-2.amazonaws.com/matargashti.mp3",
                        url="https://samarthalexasongbucket.s3.eu-west-2.amazonaws.com/matargashti.mp3",
                        expected_previous_token=None)
                )
            )
        )
        return handler_input.response_builder.response



class StartOverIntentHandler(AbstractRequestHandler):
    """Handler for start over, loop on/off, shuffle on/off intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (is_intent_name("AMAZON.StartOverIntent")(handler_input) or
                is_intent_name("AMAZON.LoopOnIntent")(handler_input) or
                is_intent_name("AMAZON.LoopOffIntent")(handler_input) or
                is_intent_name("AMAZON.ShuffleOnIntent")(handler_input) or
                is_intent_name("AMAZON.ShuffleOffIntent")(handler_input))

    def handle(self, handler_input):
        handler_input.response_builder.add_directive(
            PlayDirective(
                play_behavior=PlayBehavior.REPLACE_ALL,
                audio_item=AudioItem(
                    stream=Stream(
                        token="https://samarthalexasongbucket.s3.eu-west-2.amazonaws.com/matargashti.mp3",
                        url="https://samarthalexasongbucket.s3.eu-west-2.amazonaws.com/matargashti.mp3",
                        expected_previous_token=None)
                )
            )
        )
        return handler_input.response_builder.response

# ###################################################################

# ########## AUDIOPLAYER INTERFACE HANDLERS #########################
# This section contains handlers related to Audioplayer interface

class PlaybackStartedHandler(AbstractRequestHandler):
    """AudioPlayer.PlaybackStarted Directive received.

    Confirming that the requested audio file began playing.
    Do not send any specific response.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_request_type("AudioPlayer.PlaybackStarted")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In PlaybackStartedHandler")
        logger.info("Playback started")
        return handler_input.response_builder.response

class PlaybackFinishedHandler(AbstractRequestHandler):
    """AudioPlayer.PlaybackFinished Directive received.

    Confirming that the requested audio file completed playing.
    Do not send any specific response.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_request_type("AudioPlayer.PlaybackFinished")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In PlaybackFinishedHandler")
        logger.info("Playback finished")
        return util.stop(None, handler_input.response_builder)

class PlaybackStoppedHandler(AbstractRequestHandler):
    """AudioPlayer.PlaybackStopped Directive received.

    Confirming that the requested audio file stopped playing.
    Do not send any specific response.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_request_type("AudioPlayer.PlaybackStopped")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In PlaybackStoppedHandler")
        logger.info("Playback stopped")
        return handler_input.response_builder.response


class PlaybackFailedHandler(AbstractRequestHandler):
    """AudioPlayer.PlaybackFailed Directive received.

    Logging the error and restarting playing with no output speech and card.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_request_type("AudioPlayer.PlaybackFailed")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In PlaybackFailedHandler")
        request = handler_input.request_envelope.request
        logger.info("Playback failed: {}".format(request.error))
        return util.play(
            url=util.audio_data(request)["url"], offset=0, text=None,
            card_data=None,
            response_builder=handler_input.response_builder)


class ExceptionEncounteredHandler(AbstractRequestHandler):
    """Handler to handle exceptions from responses sent by AudioPlayer
    request.
    """
    def can_handle(self, handler_input):
        # type; (HandlerInput) -> bool
        return is_request_type("System.ExceptionEncountered")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("\n**************** EXCEPTION *******************")
        logger.info(handler_input.request_envelope)
        return handler_input.response_builder.response

# ###################################################################

# ########## PLAYBACK CONTROLLER INTERFACE HANDLERS #################
# This section contains handlers related to Playback Controller interface
# https://developer.amazon.com/docs/custom-skills/playback-controller-interface-reference.html#requests

class PlayCommandHandler(AbstractRequestHandler):
    """Handler for Play command from hardware buttons or touch control.

    This handler handles the play command sent through hardware buttons such
    as remote control or the play control from Alexa-devices with a screen.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_request_type(
            "PlaybackController.PlayCommandIssued")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In PlayCommandHandler")
        _ = handler_input.attributes_manager.request_attributes["_"]
        request = handler_input.request_envelope.request

        if util.audio_data(request)["start_jingle"]:
            if util.should_play_jingle(handler_input):
                return util.play(url=util.audio_data(request)["start_jingle"],
                                 offset=0,
                                 text=None,
                                 card_data=None,
                                 response_builder=handler_input.response_builder)

        return util.play(url=util.audio_data(request)["url"],
                         offset=0,
                         text=None,
                         card_data=None,
                         response_builder=handler_input.response_builder)


class NextOrPreviousCommandHandler(AbstractRequestHandler):
    """Handler for Next or Previous command from hardware buttons or touch
    control.

    This handler handles the next/previous command sent through hardware
    buttons such as remote control or the next/previous control from
    Alexa-devices with a screen.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (is_request_type(
            "PlaybackController.NextCommandIssued")(handler_input) or
                is_request_type(
                    "PlaybackController.PreviousCommandIssued")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In NextOrPreviousCommandHandler")
        return handler_input.response_builder.response


# class PauseCommandHandler(AbstractRequestHandler):
#     """Handler for Pause command from hardware buttons or touch control.
#
#     This handler handles the pause command sent through hardware
#     buttons such as remote control or the pause control from
#     Alexa-devices with a screen.
#     """
#     def can_handle(self, handler_input):
#         # type: (HandlerInput) -> bool
#         return is_request_type("PlaybackController.PauseCommandIssued")(
#             handler_input)
#
#     def handle(self, handler_input):
#         # type: (HandlerInput) -> Response
#         logger.info("In PauseCommandHandler")
#         return util.stop(text=None,
#                          response_builder=handler_input.response_builder)
#
# ###################################################################

# ################## EXCEPTION HANDLERS #############################
class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Catch all exception handler, log exception and
    respond with custom message.
    """
    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.info("In CatchAllExceptionHandler")
        logger.info(handler_input.request_envelope)
        logger.info(self)
        logger.error(exception, exc_info=True)
        #_ = handler_input.attributes_manager.request_attributes["_"]
        return util.stop("Goodbye.", handler_input.response_builder)

        return handler_input.response_builder.response

# ###################################################################

# ############# REQUEST / RESPONSE INTERCEPTORS #####################
class RequestLogger(AbstractRequestInterceptor):
    """Log the alexa requests."""
    def process(self, handler_input):
        # type: (HandlerInput) -> None
        logger.debug("Alexa Request: {}".format(
            handler_input.request_envelope.request))




sb.add_request_handler(LaunchRequestHandler1())
# Exception handlers
sb.add_exception_handler(CatchAllExceptionHandler())

sb.add_request_handler(NextOrPreviousIntentHandler())

sb.add_request_handler(CheckAudioInterfaceHandler())
sb.add_request_handler(SkillEventHandler())
sb.add_request_handler(PlayCommandHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(ExceptionEncounteredHandler())
sb.add_request_handler(UnhandledIntentHandler())
sb.add_request_handler(NextOrPreviousIntentHandler())
sb.add_request_handler(NextOrPreviousCommandHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(PauseIntentHandler())
sb.add_request_handler(ResumeIntentHandler())
sb.add_request_handler(StartOverIntentHandler())
sb.add_request_handler(PlaybackStartedHandler())
sb.add_request_handler(PlaybackFinishedHandler())
sb.add_request_handler(PlaybackStoppedHandler())
sb.add_request_handler(PlaybackNearlyFinishedHandler())
sb.add_request_handler(PlaybackStartedHandler())
sb.add_request_handler(PlaybackFailedHandler())
# Expose the lambda handler to register in AWS Lambda.
lambda_handler = sb.lambda_handler()