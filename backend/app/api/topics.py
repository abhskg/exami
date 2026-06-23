import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.auth_dependencies import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.topic import Topic
from app.schemas.topic import TopicCreate, TopicResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/topics", tags=["topics"])

@router.get("/", response_model=list[TopicResponse])
def list_topics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all topics created by the authenticated user.
    """
    logger.info(f"User {current_user.email} (ID: {current_user.id}) listing all topics.")
    topics = db.query(Topic).filter(Topic.user_id == current_user.id).order_by(Topic.created_at.desc()).all()
    logger.debug(f"Retrieved {len(topics)} topics for User {current_user.id}.")
    return topics

@router.post("/", response_model=TopicResponse, status_code=status.HTTP_201_CREATED)
def create_topic(
    topic_in: TopicCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new topic for the authenticated user.
    """
    logger.info(f"User {current_user.email} (ID: {current_user.id}) attempting to create topic: '{topic_in.name}'")
    
    # Check if a topic with the same name already exists for this user
    existing = db.query(Topic).filter(
        Topic.user_id == current_user.id,
        Topic.name == topic_in.name
    ).first()
    
    if existing:
        logger.warning(f"Topic creation failed: Topic with name '{topic_in.name}' already exists for User {current_user.id}.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Topic with name '{topic_in.name}' already exists."
        )
        
    topic = Topic(
        user_id=current_user.id,
        name=topic_in.name,
        description=topic_in.description
    )
    db.add(topic)
    db.commit()
    db.refresh(topic)
    
    logger.info(f"Topic '{topic.name}' (ID: {topic.id}) created successfully for User {current_user.id}.")
    return topic

