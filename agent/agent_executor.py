import logging
from agent.agent import K8sAgent
from typing_extensions import override
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.types import (
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)
from a2a.utils import new_agent_text_message, new_task, new_text_artifact

logger = logging.getLogger(__name__)


class K8sAgentExecutor(AgentExecutor):

    def __init__(self):
        self.agent = K8sAgent()

    @override
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        query = context.get_user_input()
        task = context.current_task
        
        logger.info(f"Received request: context_id={context.context_id}, user input: '{query[:50]}...' (truncated)")

        if not context.message:
            logger.error("No message provided in context")
            raise Exception('No message provided')

        if not task:
            logger.info(f"Creating new task for context_id={context.context_id}")
            task = new_task(context.message)
            event_queue.enqueue_event(task)
            logger.info(f"New task created: task_id={task.id}")
            
        # invoke the underlying agent, using streaming results
        logger.info(f"Starting agent stream for task_id={task.id}, context_id={task.contextId}")
        async for event in self.agent.stream(query, task.contextId):
            if event['is_task_complete']:
                logger.info(f"Task completed: task_id={task.id}, context_id={task.contextId}")
                logger.debug(f"Task completion content: '{event['content'][:100]}...' (truncated)")
                
                event_queue.enqueue_event(
                    TaskArtifactUpdateEvent(
                        append=False,
                        contextId=task.contextId,
                        taskId=task.id,
                        lastChunk=True,
                        artifact=new_text_artifact(
                            name='current_result',
                            description='Result of request to agent.',
                            text=event['content'],
                        ),
                    )
                )
                logger.info(f"Sent TaskArtifactUpdateEvent: task_id={task.id}, lastChunk=True")
                
                event_queue.enqueue_event(
                    TaskStatusUpdateEvent(
                        status=TaskStatus(state=TaskState.completed),
                        final=True,
                        contextId=task.contextId,
                        taskId=task.id,
                    )
                )
                logger.info(f"Sent TaskStatusUpdateEvent: task_id={task.id}, state=completed, final=True")
                
            elif event['require_user_input']:
                logger.info(f"User input required: task_id={task.id}, context_id={task.contextId}")
                logger.debug(f"User input request content: '{event['content'][:100]}...' (truncated)")
                
                event_queue.enqueue_event(
                    TaskStatusUpdateEvent(
                        status=TaskStatus(
                            state=TaskState.input_required,
                            message=new_agent_text_message(
                                event['content'],
                                task.contextId,
                                task.id,
                            ),
                        ),
                        final=True,
                        contextId=task.contextId,
                        taskId=task.id,
                    )
                )
                logger.info(f"Sent TaskStatusUpdateEvent: task_id={task.id}, state=input_required, final=True")
                
            else:
                logger.info(f"Task in progress: task_id={task.id}, context_id={task.contextId}")
                logger.debug(f"Progress update content: '{event['content'][:100]}...' (truncated)")
                
                event_queue.enqueue_event(
                    TaskStatusUpdateEvent(
                        status=TaskStatus(
                            state=TaskState.working,
                            message=new_agent_text_message(
                                event['content'],
                                task.contextId,
                                task.id,
                            ),
                        ),
                        final=False,
                        contextId=task.contextId,
                        taskId=task.id,
                    )
                )
                logger.info(f"Sent TaskStatusUpdateEvent: task_id={task.id}, state=working, final=False")

    @override
    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        logger.warning(f"Cancel requested for context_id={context.context_id}, but not supported")
        raise Exception('cancel not supported')
