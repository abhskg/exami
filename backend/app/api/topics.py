import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth_dependencies import get_current_user
from app.core.database import get_db
from app.models.topic import Topic
from app.models.user import User
from app.schemas.topic import TopicCreate, TopicResponse, TopicUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/topics", tags=["topics"])


@router.get("/", response_model=list[TopicResponse])
def list_topics(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    List all topics created by the authenticated user.
    """
    logger.info(f"User {current_user.email} (ID: {current_user.id}) listing all topics.")
    topics = (
        db.query(Topic)
        .filter(Topic.user_id == current_user.id)
        .order_by(Topic.created_at.desc())
        .all()
    )
    logger.debug(f"Retrieved {len(topics)} topics for User {current_user.id}.")
    return topics


@router.post("/", response_model=TopicResponse, status_code=status.HTTP_201_CREATED)
def create_topic(
    topic_in: TopicCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new topic for the authenticated user.
    """
    logger.info(
        f"User {current_user.email} (ID: {current_user.id}) attempting to create topic: '{topic_in.name}'"
    )

    # Check if a topic with the same name already exists for this user
    existing = (
        db.query(Topic)
        .filter(Topic.user_id == current_user.id, Topic.name == topic_in.name)
        .first()
    )

    if existing:
        logger.warning(
            f"Topic creation failed: Topic with name '{topic_in.name}' already exists for User {current_user.id}."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Topic with name '{topic_in.name}' already exists.",
        )

    topic = Topic(user_id=current_user.id, name=topic_in.name, description=topic_in.description)
    db.add(topic)
    db.commit()
    db.refresh(topic)

    logger.info(
        f"Topic '{topic.name}' (ID: {topic.id}) created successfully for User {current_user.id}."
    )
    return topic


@router.put("/{topic_id}", response_model=TopicResponse)
def update_topic(
    topic_id: str,
    topic_in: TopicUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update the name and/or description of an existing topic owned by the authenticated user.
    """
    topic = (
        db.query(Topic)
        .filter(Topic.id == topic_id, Topic.user_id == current_user.id)
        .first()
    )
    if not topic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found.")

    if topic_in.name is not None:
        # Check uniqueness (excluding self)
        conflict = (
            db.query(Topic)
            .filter(
                Topic.user_id == current_user.id,
                Topic.name == topic_in.name,
                Topic.id != topic_id,
            )
            .first()
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Topic with name '{topic_in.name}' already exists.",
            )
        topic.name = topic_in.name

    if topic_in.description is not None:
        topic.description = topic_in.description

    db.commit()
    db.refresh(topic)
    logger.info(f"Topic '{topic.name}' (ID: {topic.id}) updated by User {current_user.id}.")
    return topic


@router.delete("/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_topic(
    topic_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a topic and all its associated data (documents, questions, sessions, tags)
    owned by the authenticated user.
    """
    topic = (
        db.query(Topic)
        .filter(Topic.id == topic_id, Topic.user_id == current_user.id)
        .first()
    )
    if not topic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found.")

    logger.warning(
        f"User {current_user.id} deleting Topic '{topic.name}' (ID: {topic.id}) and all its data."
    )
    db.delete(topic)
    db.commit()

